// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  useCallback,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import {
  getStorageItem,
  removeStorageItem,
  setStorageItem,
  watchStorageItem,
} from '@amdenterpriseai/utils/app';
import { getAppConfig, AppConfig } from '@/lib/app/app-config';
import { NamespacesResponse } from '@/types/namespaces';
import { fetchNamespaces } from '@/lib/app/namespaces';

interface ProjectContextType {
  isStandaloneMode: boolean;
  activeProject: string | null;
  projects: NamespacesResponse['data'];
  isLoading: boolean;
  isInitialized: boolean;
  projectError: unknown | null;
  refetchProjects: () => void;
  setActiveProject: (projectId: string) => void;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

interface ProjectProviderProps {
  children: ReactNode;
}

/** Picks the best available project: prefers the one stored in localStorage
 *  if still valid, falls back to auto-selecting when only one project exists,
 *  or returns null to let the user choose. */
const resolveActiveProject = (
  projects: NamespacesResponse['data'],
): string | null => {
  const storedProject = getStorageItem('activeProject');
  const storedProjectExists =
    storedProject && projects.some((p) => p.id === storedProject);

  if (storedProjectExists) return storedProject;
  if (projects.length === 1) return projects[0].id;
  return null;
};

export const ProjectProvider = ({ children }: ProjectProviderProps) => {
  const [activeProject, setActiveProjectState] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const queryClient = useQueryClient();

  const { data: appConfig } = useQuery<AppConfig>({
    queryKey: ['appConfig'],
    queryFn: getAppConfig,
    // When the app config is not available or throwing error, useQuery will use the initialData
    initialData: {
      isStandaloneMode: false,
      defaultNamespace: null,
    },
  });

  const { isStandaloneMode, defaultNamespace } = appConfig;

  const { data, isLoading, error, refetch } = useQuery<NamespacesResponse>({
    queryKey: ['user-projects'],
    queryFn: fetchNamespaces,
    refetchInterval: 10000,
    enabled: !isStandaloneMode,
  });

  const projects: NamespacesResponse['data'] =
    isStandaloneMode && defaultNamespace
      ? [
          {
            id: defaultNamespace,
            name: defaultNamespace,
          },
        ]
      : data?.data || [];

  const invalidateProjectQueries = useCallback((): void => {
    queryClient.invalidateQueries({ queryKey: ['project'] });
  }, [queryClient]);

  // Updates active project state and syncs to localStorage.
  const applyActiveProject = useCallback((project: string | null): void => {
    setActiveProjectState(project);
    if (project) {
      setStorageItem('activeProject', project);
    } else {
      removeStorageItem('activeProject');
    }
  }, []);

  // Runs once on mount to pick the initial active project.
  useEffect(() => {
    if (isInitialized || isLoading) return;

    const project = isStandaloneMode
      ? defaultNamespace
      : resolveActiveProject(projects);

    applyActiveProject(project);

    setIsInitialized(true);
  }, [
    isStandaloneMode,
    defaultNamespace,
    projects,
    isInitialized,
    isLoading,
    applyActiveProject,
  ]);

  // Runs continuously (projects refetch every 10s) to reset activeProject
  // when it's no longer valid (e.g., user removed from project, mode switch).
  useEffect(() => {
    if (isStandaloneMode || isLoading) return;

    // If there are no projects returned from API
    if (projects.length === 0) {
      if (activeProject) {
        applyActiveProject(null);
        invalidateProjectQueries();
      }
      return;
    }

    // No active project to validate
    if (!activeProject) return;

    // Active project is still in the projects list
    const activeProjectExists = projects.some((p) => p.id === activeProject);
    if (activeProjectExists) return;

    const project = resolveActiveProject(projects);
    applyActiveProject(project);

    invalidateProjectQueries();
  }, [
    isStandaloneMode,
    activeProject,
    projects,
    isLoading,
    applyActiveProject,
    invalidateProjectQueries,
  ]);

  // Used to reset activeProject when it's changed in another tab
  useEffect(() => {
    if (isStandaloneMode) return;

    return watchStorageItem('activeProject', (projectId) => {
      if (projectId !== activeProject) {
        setActiveProjectState(projectId);
        invalidateProjectQueries();
      }
    });
  }, [isStandaloneMode, activeProject, invalidateProjectQueries]);

  const setActiveProject = (projectId: string): void => {
    if (projectId !== activeProject) {
      applyActiveProject(projectId);
      invalidateProjectQueries();
    }
  };

  const refetchProjects = (): void => {
    void refetch();
  };

  const value: ProjectContextType = {
    isStandaloneMode,
    activeProject,
    projects,
    isLoading,
    isInitialized,
    projectError: error ?? null,
    refetchProjects,
    setActiveProject,
  };

  return (
    <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
  );
};

export const useProject = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
};
