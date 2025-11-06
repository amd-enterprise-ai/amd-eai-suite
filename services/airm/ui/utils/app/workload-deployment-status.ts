// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { WorkloadStatus } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

export enum DeploymentStatus {
  NOT_DEPLOYED = 'not_deployed',
  DEPLOYING = 'deploying',
  DEPLOYED = 'deployed',
  UNDEPLOYING = 'undeploying',
  DEPLOYMENT_FAILED = 'deployment_failed',
}

/**
 * Determines the deployment status based on workload status
 *
 * Rules:
 * - workload is not deployed -> workload with Deleted/Terminated status or null or undefined workload
 * - workload is undeploying -> there would be the workload with Deleting status. Could also be DeleteFailed
 * - workload is deploying -> there would be the workload with Pending status
 * - workload is deployed -> it should only be Running if it's fully deployed and ready to be used
 * - Deployment Failed -> workload status Failed
 */
export const getDeploymentStatus = (
  workload?: Workload | null,
): DeploymentStatus => {
  // No workload or null/undefined workload = not deployed
  if (!workload) {
    return DeploymentStatus.NOT_DEPLOYED;
  }

  const { status } = workload;

  switch (status) {
    // Not deployed states
    case WorkloadStatus.DELETED:
    case WorkloadStatus.TERMINATED:
      return DeploymentStatus.NOT_DEPLOYED;

    // Deploying state
    case WorkloadStatus.PENDING:
      return DeploymentStatus.DEPLOYING;

    // Deployed state (fully ready)
    case WorkloadStatus.RUNNING:
      return DeploymentStatus.DEPLOYED;

    // Undeploying states
    case WorkloadStatus.DELETING:
    case WorkloadStatus.DELETE_FAILED:
      return DeploymentStatus.UNDEPLOYING;

    // Deployment failed state
    case WorkloadStatus.FAILED:
      return DeploymentStatus.DEPLOYMENT_FAILED;

    // Handle edge cases - treat as not deployed
    case WorkloadStatus.ADDED:
    case WorkloadStatus.COMPLETE:
    case WorkloadStatus.UNKNOWN:
    default:
      return DeploymentStatus.NOT_DEPLOYED;
  }
};

/**
 * Helper functions to check specific deployment states
 */
export const isDeployed = (workload?: Workload | null): boolean => {
  return getDeploymentStatus(workload) === DeploymentStatus.DEPLOYED;
};

export const isDeploying = (workload?: Workload | null): boolean => {
  return getDeploymentStatus(workload) === DeploymentStatus.DEPLOYING;
};

export const isUndeploying = (workload?: Workload | null): boolean => {
  return getDeploymentStatus(workload) === DeploymentStatus.UNDEPLOYING;
};

export const isNotDeployed = (workload?: Workload | null): boolean => {
  return getDeploymentStatus(workload) === DeploymentStatus.NOT_DEPLOYED;
};

export const isDeploymentFailed = (workload?: Workload | null): boolean => {
  return getDeploymentStatus(workload) === DeploymentStatus.DEPLOYMENT_FAILED;
};
