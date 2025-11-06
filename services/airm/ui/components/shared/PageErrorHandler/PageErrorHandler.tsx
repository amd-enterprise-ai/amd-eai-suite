// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useRouter } from 'next/router';

import { fetchSubmittableProjects } from '@/services/app/projects';

import { ErrorCodes, ErrorMessageProps } from '@/types/errors';

import ErrorMessage from './ErrorMessage';
import LoadingState from './LoadingState';

// Pages that require submittable projects
const SUBMITTABLE_PROJECTS_REQUIRED_PAGES = [
  '/api-keys',
  '/chat',
  '/datasets',
  '/models',
  '/workloads',
  '/workspaces',
  '/workbench-secrets',
];

interface PageValidationConfig {
  pages: string[];
  validator: () => Promise<{
    isValid: boolean;
    errorMessage?: string;
    errorCode?: string;
  }>;
}

/**
 * Hook for validating page access requirements using custom validator functions.
 *
 * Automatically runs validation when the pathname changes and manages loading/error states.
 * Only validates pages that match the configured page patterns. Uses Next.js router internally
 * to track pathname changes and prevent concurrent validations.
 *
 * @param pageValidationConfigs - Array of validation configurations, each containing:
 *   - pages: Array of page paths that require this validation
 *   - validator: Async function that returns validation result with isValid, errorMessage, and errorCode
 *
 * @returns Object containing:
 *   - error: Current validation error (ErrorMessageProps | null)
 *   - isValidating: Whether validation is currently in progress
 *   - validate: Function to manually trigger validation
 *
 * @example
 * ```typescript
 * const configs = [{
 *   pages: ['/admin', '/settings'],
 *   validator: async () => {
 *     const hasPermission = await checkAdminPermission();
 *     return {
 *       isValid: hasPermission,
 *       errorMessage: 'Admin access required',
 *       errorCode: ErrorCodes.INSUFFICIENT_PERMISSIONS
 *     };
 *   }
 * }];
 *
 * const { error, isValidating, validate } = usePageValidations(configs);
 * ```
 */
const usePageValidations = (pageValidationConfigs: PageValidationConfig[]) => {
  const router = useRouter();
  const [error, setError] = useState<ErrorMessageProps | null>(null);
  const [validatedPath, setValidatedPath] = useState<string | null>(null);
  const isValidatingRef = useRef<boolean>(false);

  const validate = useCallback(async () => {
    if (isValidatingRef.current) return;
    isValidatingRef.current = true;

    setValidatedPath(null);
    setError(null);

    const currentPageValidationConfigs = pageValidationConfigs.filter(
      (config) =>
        config.pages.some(
          (page) =>
            router.pathname === page || router.pathname.startsWith(page + '/'),
        ),
    );

    if (currentPageValidationConfigs.length === 0) {
      setValidatedPath(router.pathname);
      isValidatingRef.current = false;
      return;
    }

    try {
      const results = await Promise.all(
        currentPageValidationConfigs.map((config) => config.validator()),
      );
      const failedValidation = results.find((result) => !result.isValid);
      if (failedValidation)
        setError({
          message: failedValidation.errorMessage,
          code: failedValidation.errorCode,
        });
    } catch (_) {
      setError({
        message: 'Validation process failed',
        code: ErrorCodes.NETWORK_ERROR,
      });
    } finally {
      setValidatedPath(router.pathname);
      isValidatingRef.current = false;
    }
  }, [pageValidationConfigs, router.pathname]);

  useEffect(() => {
    validate();
  }, [router.pathname, validate]);

  return { error, isValidating: validatedPath !== router.pathname, validate };
};

/**
 * Validates whether the current user has submittable projects.
 *
 * Fetches the user's submittable projects and checks if they have at least one project
 * available for submission. This is required for accessing AI Workbench features.
 *
 * @returns Promise resolving to validation result object:
 *   - isValid: true if user has submittable projects, false otherwise
 *   - errorCode: Error code if validation fails (NO_SUBMITTABLE_PROJECTS or NETWORK_ERROR)
 *
 * @example
 * ```typescript
 * const result = await hasProjectsValidator();
 * if (!result.isValid) {
 *   console.log('Validation failed:', result.errorCode);
 * }
 * ```
 */
const hasProjectsValidator = async () => {
  try {
    const response = await fetchSubmittableProjects();

    if (response?.projects?.length === 0)
      return {
        isValid: false,
        errorCode: ErrorCodes.NO_SUBMITTABLE_PROJECTS,
      };

    return {
      isValid: true,
    };
  } catch (_) {
    return {
      isValid: false,
      errorCode: ErrorCodes.NETWORK_ERROR,
    };
  }
};

/**
 * React component that provides global error handling and page access validation.
 *
 * This component wraps the application and validates API requirements for AI Workbench pages
 * before rendering content. Validates that users have submittable projects for all
 * AI Workbench pages (chat, datasets, models, workloads, workspaces, api-keys, workbench-secrets).
 *
 * Features:
 * - Automatic validation on route changes
 * - Loading state management during validation
 * - Error display with refresh functionality
 * - Prevention of concurrent validations
 * - Validates only AI Workbench pages
 *
 * @param props - Component props
 * @param props.children - Child components to render when validation passes
 *
 * @returns ErrorMessage component if validation fails, LoadingState during validation,
 *          or children when validation passes
 *
 * @example
 * ```tsx
 * <PageErrorHandler>
 *   <MyAppContent />
 * </PageErrorHandler>
 * ```
 */
const PageErrorHandler: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const pageValidationConfigs: PageValidationConfig[] = useMemo(
    () => [
      {
        pages: SUBMITTABLE_PROJECTS_REQUIRED_PAGES,
        validator: hasProjectsValidator,
      },
    ],
    [],
  );

  const { error, isValidating, validate } = usePageValidations(
    pageValidationConfigs,
  );

  if (error)
    return (
      <ErrorMessage
        message={error.message}
        code={error.code}
        onRefresh={validate}
      />
    );
  if (isValidating) return <LoadingState />;
  return <>{children}</>;
};

export default PageErrorHandler;
