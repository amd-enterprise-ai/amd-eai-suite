// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useRouter } from 'next/router';

import { useProject } from '@/contexts/ProjectContext';
import { ErrorCodes, ErrorMessageProps } from '@amdenterpriseai/types';
import { ProjectSelectPrompt } from '@/components/shared/ProjectSelect';

import ErrorMessage from './ErrorMessage';
import LoadingState from './LoadingState';

/**
 * Guards page rendering with project context state.
 * Shows loading while project context initializes, displays project-related errors when required,
 * and optionally renders a project selection prompt when no active project is selected.
 *
 * @param props - Component props
 * @param props.children - Content rendered when checks pass
 * @param props.projectRequired - Enables project-required validation
 * @param props.noActiveProjectComponent - Optional UI shown when no active project is selected
 *
 * @returns Loading state, error view, project prompt, or children
 */
export const PageErrorHandler: React.FC<{
  children: React.ReactNode;
  projectRequired?: boolean;
  noActiveProjectComponent?: React.ReactNode;
}> = ({ children, projectRequired, noActiveProjectComponent }) => {
  const router = useRouter();
  const { activeProject, projects, isLoading, projectError, refetchProjects } =
    useProject();

  const projectFromUrl = router.query.project as string | undefined;

  const error = useMemo<ErrorMessageProps | null>(() => {
    if (!projectRequired || isLoading) return null;
    const hasProjectFetchError = Boolean(projectError) && projects.length === 0;
    if (hasProjectFetchError) {
      return { code: ErrorCodes.FETCH_FAILED };
    }
    if (projects.length === 0) {
      return { code: ErrorCodes.NO_SUBMITTABLE_PROJECTS };
    }
    if (projectFromUrl && !activeProject) {
      return { code: ErrorCodes.PROJECT_NOT_FOUND };
    }
    return null;
  }, [
    projectRequired,
    isLoading,
    projectError,
    projects,
    projectFromUrl,
    activeProject,
  ]);

  if (isLoading) return <LoadingState />;

  if (error) {
    if (error.code === ErrorCodes.PROJECT_NOT_FOUND) {
      return <ProjectSelectPrompt errorCode={error.code} />;
    }
    return (
      <ErrorMessage
        message={error.message}
        code={error.code}
        onRefresh={refetchProjects}
      />
    );
  }

  const showProjectSelectPrompt =
    projectRequired &&
    projects.length > 0 &&
    !activeProject &&
    !projectFromUrl &&
    noActiveProjectComponent;

  if (showProjectSelectPrompt) return <>{noActiveProjectComponent}</>;

  return <>{children}</>;
};

export default PageErrorHandler;
