// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Application error types for consistent error handling across the app
 */

export interface ErrorMessageProps {
  message?: string;
  code?: string;
  onRefresh?: () => void;
}

export enum ErrorCodes {
  NO_SUBMITTABLE_PROJECTS = 'noSubmittableProjects',
  NETWORK_ERROR = 'network',
}
