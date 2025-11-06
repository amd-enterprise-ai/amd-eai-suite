// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterBasicInfo } from './clusters';
import { ProjectFormFields } from './enums/project-form-fields';
import { ProjectStatus } from './enums/projects';
import { Quota, QuotaAllocationFormData, UpdateQuotaRequest } from './quotas';

export type ProjectBasicInfo = {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  statusReason: string | null;
  clusterId: string;
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
};

export type ProjectWithResourceAllocation = Project & {
  gpuAllocationPercentage: number;
  cpuAllocationPercentage: number;
  memoryAllocationPercentage: number;
  gpuAllocationExceeded: boolean;
  cpuAllocationExceeded: boolean;
  memoryAllocationExceeded: boolean;
};

type BaseUser = {
  id: string;
  role: string;
  email: string;
};

export type UserInProject = BaseUser & {
  firstName: string;
  lastName: string;
  lastActiveAt?: string;
};

export type InvitedUserInProject = BaseUser & {};

export type ProjectWithMembers = Project & {
  users: UserInProject[];
  invitedUsers: InvitedUserInProject[];
};

export type ClusterProjectsResponse = {
  projects: ProjectWithResourceAllocation[];
};

export type ProjectsResponse = {
  projects: ProjectWithResourceAllocation[];
};

export type CreateProjectRequest = {
  name: string;
  description: string;
  cluster_id: string;
  quota: UpdateQuotaRequest;
};

export type UpdateProjectRequest = {
  id: string;
  description: string;
  quota: UpdateQuotaRequest;
};

export type BaseProjectFormData = {
  [key in ProjectFormFields]: string;
};

export type ProjectGeneralFormData = BaseProjectFormData;
export type ProjectQuotaFormData = QuotaAllocationFormData;

export type InviteMemberFormFieldNames = 'users';
export type InviteMemberFormData = {
  [key in InviteMemberFormFieldNames]: string | string[] | undefined;
};
