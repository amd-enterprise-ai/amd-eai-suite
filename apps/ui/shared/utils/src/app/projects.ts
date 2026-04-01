// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ProjectStatus } from '@amdenterpriseai/types';
import { Project, ProjectWithMembers } from '@amdenterpriseai/types';
import { InvitedUser, User } from '@amdenterpriseai/types';

export const getProjectDashboardUrl = (id: string) => `/projects/${id}`;
export const getProjectEditUrl = (id: string) => `/projects/${id}/edit`;

export const getCandidateUsersForProject = (
  project: ProjectWithMembers,
  allUsers?: User[],
): User[] => {
  const usersInProject = new Set(project.users.map((u) => u.id));
  return (
    allUsers
      ?.filter((u) => !usersInProject.has(u.id))
      .sort((a, b) => a.email.localeCompare(b.email)) || []
  );
};

export const getCandidateInvitedUsersForProject = (
  project: ProjectWithMembers,
  allInvitedUsers?: InvitedUser[],
): InvitedUser[] => {
  const invitedUsersInGroup = new Set(project.invitedUsers.map((u) => u.id));
  return (
    allInvitedUsers
      ?.filter((u) => !invitedUsersInGroup.has(u.id))
      .sort((a, b) => a.email.localeCompare(b.email)) || []
  );
};

export const doesProjectDataNeedToBeRefreshed = (projects: Project[]) => {
  return projects.some(
    (c) =>
      c.status == ProjectStatus.PENDING || c.status == ProjectStatus.DELETING,
  );
};
