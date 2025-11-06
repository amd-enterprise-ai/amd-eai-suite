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

import { fetchSubmittableProjects } from '@/services/app/projects';
import {
  getStorageItem,
  setStorageItem,
  watchStorageItem,
} from '@/utils/app/storage';
import { ProjectsResponse } from '@/types/projects';

interface ProjectContextType {
  activeProject: string | null;
  projects: any[];
  isLoading: boolean;
  setActiveProject: (projectId: string) => void;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

interface ProjectProviderProps {
  children: ReactNode;
}

export const ProjectProvider = ({ children }: ProjectProviderProps) => {
  const [activeProject, setActiveProjectState] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<ProjectsResponse>({
    queryKey: ['user-projects'],
    queryFn: fetchSubmittableProjects,
    refetchInterval: 10000,
  });

  const projects = data?.projects || [];

  const invalidateProjectQueries = useCallback((): void => {
    queryClient.invalidateQueries({ queryKey: ['project'] });
  }, [queryClient]);

  // Initialize active project from localStorage on mount
  useEffect(() => {
    if (isInitialized) return;

    const storedProject = getStorageItem('activeProject');

    if (projects.length > 0) {
      if (storedProject && projects.some((p) => p.id === storedProject)) {
        setActiveProjectState(storedProject);
      } else if (projects.length === 1) {
        setActiveProjectState(projects[0].id);
        setStorageItem('activeProject', projects[0].id);
      }
      setIsInitialized(true);
    }
  }, [projects, isInitialized]);

  // Watch for changes from other tabs/windows
  useEffect(() => {
    const cleanupFn = watchStorageItem('activeProject', (projectId) => {
      if (projectId !== activeProject) {
        setActiveProjectState(projectId);
        invalidateProjectQueries();
      }
    });

    return () => {
      if (typeof cleanupFn === 'function') {
        cleanupFn();
      }
    };
  }, [activeProject, invalidateProjectQueries]);

  const setActiveProject = (projectId: string): void => {
    if (projectId !== activeProject) {
      setActiveProjectState(projectId);
      setStorageItem('activeProject', projectId);
      invalidateProjectQueries();
    }
  };

  const value: ProjectContextType = {
    activeProject,
    projects,
    isLoading,
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
