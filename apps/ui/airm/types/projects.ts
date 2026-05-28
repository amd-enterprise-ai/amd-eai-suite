// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { UserRole } from '@amdenterpriseai/types';
import { ClusterBasicInfo } from './clusters';
import { GpuPreemptionPolicy } from './enums/gpu-preemption-policy';
import {
  ProjectFormFields,
  ProjectGpuPreemptionFormFields,
} from './enums/project-form-fields';
import { ProjectStatus } from './enums/projects';
import { Quota, QuotaAllocationFormData, UpdateQuotaRequest } from './quotas';
import { InvitedUser, User } from './users';

export type GpuPreemptionConfigDisabled = {
  enabled: false;
  threshold: null;
  gracePeriod: null;
  policy: null;
};

export type GpuPreemptionConfigEnabled = {
  enabled: true;
  threshold: number;
  gracePeriod: number;
  policy: GpuPreemptionPolicy;
};

export type GpuPreemptionConfig =
  | GpuPreemptionConfigDisabled
  | GpuPreemptionConfigEnabled;

/**
 * Shape used for read-only UI: when `enabled` is true the API may still return null
 * for policy, grace period, or threshold. Normal `GpuPreemptionConfig` values are
 * assignable (narrower fields widen to `T | null`).
 */
export type GpuPreemptionReadOnlyConfig =
  | GpuPreemptionConfigDisabled
  | {
      enabled: true;
      policy: GpuPreemptionPolicy | null;
      gracePeriod: number | null;
      threshold: number | null;
    };

export type ProjectBasicInfo = {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  statusReason: string | null;
  clusterId: string;
  gpuPreemption: GpuPreemptionConfig;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  statusReason: string | null;
  clusterId: string;
  quota: Quota;
  cluster: ClusterBasicInfo;
  gpuPreemption: GpuPreemptionConfig;
};

export type ProjectWithResourceAllocation = Project & {
  gpuAllocationPercentage: number;
  cpuAllocationPercentage: number;
  memoryAllocationPercentage: number;
  gpuAllocationExceeded: boolean;
  cpuAllocationExceeded: boolean;
  memoryAllocationExceeded: boolean;
};

export type ProjectWithMembers = Project & {
  users: User[];
  invitedUsers: InvitedUser[];
};

export type ClusterProjectsResponse = {
  data: ProjectWithResourceAllocation[];
};

export type ProjectsResponse = {
  data: ProjectWithResourceAllocation[];
};

export type CreateProjectRequest = {
  name: string;
  description: string;
  clusterId: string;
  quota: UpdateQuotaRequest;
  gpuPreemption: GpuPreemptionConfig;
};

export type UpdateProjectRequest = {
  id: string;
  description: string;
  quota: UpdateQuotaRequest;
  gpuPreemption: GpuPreemptionConfig;
};

export type BaseProjectFormData = {
  [key in ProjectFormFields]: string;
};

export type CreateProjectFormData = BaseProjectFormData & {
  [ProjectGpuPreemptionFormFields.ENABLED]: boolean;
  [ProjectGpuPreemptionFormFields.POLICY]?: GpuPreemptionPolicy;
  [ProjectGpuPreemptionFormFields.THRESHOLD]?: number;
  [ProjectGpuPreemptionFormFields.GRACE_PERIOD]?: number;
};

export type ProjectGeneralFormData = BaseProjectFormData;
export type ProjectQuotaFormData = QuotaAllocationFormData;

export type InviteMemberFormFieldNames = 'users';
export type InviteMemberFormData = {
  [key in InviteMemberFormFieldNames]: string | string[] | undefined;
};

export const GPU_PREEMPTION_DISABLED: GpuPreemptionConfigDisabled =
  Object.freeze({
    enabled: false,
    threshold: null,
    gracePeriod: null,
    policy: null,
  });
