// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterBasicInfo } from './clusters';
import { UserRole } from './enums/user-roles';
import { QuotaBase } from './quotas';

export type ProjectInUser = {
  id: string;
  name: string;
  description: string;
  clusterId: string;
  quota: QuotaBase;
  cluster: ClusterBasicInfo;
};

type BaseUser = {
  id: string;
  email: string;
  role: UserRole;
};

export type User = BaseUser & {
  firstName: string;
  lastName: string;
  lastActiveAt?: string;
};

export type UserWithProjects = User & {
  projects: ProjectInUser[];
};

export type InvitedUser = BaseUser & {
  invitedAt: string;
  invitedBy: string;
};

export type Users = User[];

export type UsersResponse = {
  users: Users;
};

export type InvitedUsersResponse = {
  invitedUsers: InvitedUser[];
};

export type UserResponse = User;

export type InviteUserRequest = {
  email: string;
  roles: UserRole[];
  project_ids: string[];
};

export type UpdateUserRequest = {
  id: string;
  firstName: string;
  lastName: string;
};

export type InviteUserFormData = {
  email: string | string[];
  roles: string | string[];
  projectIds?: string | string[];
};

export type UserFormField = 'firstName' | 'lastName' | 'email';

export type UserFormData = {
  [key in UserFormField]: string;
};

export type AssignUserRoleFormFieldNames = 'role';

export type AssignUserRoleFormData = {
  [key in AssignUserRoleFormFieldNames]: string;
};

export type AssignProjectFormData = {
  project: string | undefined;
};
