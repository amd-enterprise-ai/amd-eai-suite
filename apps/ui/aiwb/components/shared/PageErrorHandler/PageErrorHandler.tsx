// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useProject } from '@/contexts/ProjectContext';
import { ErrorCodes, ErrorMessageProps } from '@amdenterpriseai/types';

import ErrorMessage from './ErrorMessage';
import LoadingState from './LoadingState';

/**
 * Guards page rendering with project context state.
 * Shows loading while project context initializes, displays project-related errors when required,
 * and optionally renders a project selection prompt when no active project is set.
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
  const {
    activeProject,
    projects,
    isLoading,
    isInitialized,
    projectError,
    refetchProjects,
  } = useProject();

  const error = useMemo<ErrorMessageProps | null>(() => {
    if (!projectRequired || isLoading || !isInitialized) return null;
    const hasProjectFetchError = Boolean(projectError) && projects.length === 0;
    if (hasProjectFetchError) {
      return { code: ErrorCodes.FETCH_FAILED };
    }
    if (projects.length === 0) {
      return { code: ErrorCodes.NO_SUBMITTABLE_PROJECTS };
    }
    return null;
  }, [projectRequired, isLoading, isInitialized, projectError, projects]);

  // Wait for complete initialization before making any rendering decisions
  // This prevents UI "blinking" by ensuring all async operations complete first
  if (
    isLoading || // Projects fetch in progress
    (projectRequired && !isInitialized) // Active project initialization in progress
  )
    return <LoadingState />;

  // After all loading is complete, check if we need to show project selection prompt
  const showProjectSelectPrompt =
    projectRequired &&
    projects.length > 0 &&
    !activeProject &&
    noActiveProjectComponent;

  if (showProjectSelectPrompt) return <>{noActiveProjectComponent}</>;

  if (error)
    return (
      <ErrorMessage
        message={error.message}
        code={error.code}
        onRefresh={refetchProjects}
      />
    );

  return <>{children}</>;
};

export default PageErrorHandler;
