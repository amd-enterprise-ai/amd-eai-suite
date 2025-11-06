// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { generateMockProjects } from '@/__mocks__/utils/project-mock';
import {
  doesDataNeedToBeRefreshed,
  getCandidateInvitedUsersForProject,
  getCandidateUsersForProject,
  getProjectDashboardUrl,
  getProjectEditUrl,
} from '@/utils/app/projects';

import { ClusterStatus } from '@/types/enums/cluster-status';
import { ProjectStatus } from '@/types/enums/projects';
import { QuotaStatus } from '@/types/enums/quotas';
import { ProjectWithMembers } from '@/types/projects';
import { InvitedUser, User } from '@/types/users';

describe('getCandidateUsersForProject', () => {
  const project = {
    ...generateMockProjects(1)[0],
    users: [
      {
        id: '1',
        firstName: 'f',
        lastName: 'l',
        role: 'Platform Administrator',
        email: 'user@email.com',
      },
    ],
    invitedUsers: [],
  } as ProjectWithMembers;

  it('should return empty array if the overlap is complete', () => {
    const users = [
      {
        id: '1',
        firstName: 'f',
        lastName: 'l',
        email: 'email',
      },
    ] as User[];
    expect(getCandidateUsersForProject(project, users).length).toBe(0);
  });

  it('should return empty array if allUsers is undefined', () => {
    expect(getCandidateUsersForProject(project, undefined).length).toBe(0);
  });

  it('should return candidate users if not all users are in the group', () => {
    const users = [
      {
        id: '2',
        firstName: 'f',
        lastName: 'l',
        email: 'email',
      },
    ] as User[];
    expect(getCandidateUsersForProject(project, users).length).toBe(1);
  });
});

describe('getCandidateInvitedUsersForProject', () => {
  const project = {
    id: '1',
    clusterId: '1',
    name: 'grp',
    description: 'desc',
    status: ProjectStatus.READY,
    statusReason: null,
    quota: {
      status: QuotaStatus.PENDING,
      cpuMilliCores: 1000,
      gpuCount: 1,
      memoryBytes: 2000,
      ephemeralStorageBytes: 10000,
    },
    cluster: {
      id: '1',
      name: 'cluster-1',
      lastHeartbeatAt: '2025-03-11T23:24:03.733668Z',
      status: ClusterStatus.HEALTHY,
    },
    users: [],
    invitedUsers: [
      {
        id: 'user1',
        email: 'email@company.com',
        role: 'Platform Administrator',
      },
    ],
  } as ProjectWithMembers;

  it('should return empty array if the overlap is complete', () => {
    const invitedUsers = [
      {
        id: 'user1',
        email: 'email',
        role: 'Platform Administrator',
      },
    ] as InvitedUser[];
    expect(
      getCandidateInvitedUsersForProject(project, invitedUsers).length,
    ).toBe(0);
  });

  it('should return empty array if allUsers is undefined', () => {
    expect(getCandidateInvitedUsersForProject(project, undefined).length).toBe(
      0,
    );
  });

  it('should return candidate users if not all users are in the group', () => {
    const invitedUsers = [
      {
        id: '2',
        email: 'email',
        role: 'Platform Administrator',
      },
    ] as InvitedUser[];
    expect(
      getCandidateInvitedUsersForProject(project, invitedUsers).length,
    ).toBe(1);
  });
});

describe('getProjectDashboardUrl', () => {
  it('should return the correct dashboard URL for a given project id', () => {
    expect(getProjectDashboardUrl('123')).toBe('/projects/123');
    expect(getProjectDashboardUrl('abc')).toBe('/projects/abc');
  });
});

describe('getProjectEditUrl', () => {
  it('should return the correct edit URL for a given project id', () => {
    expect(getProjectEditUrl('123')).toBe('/projects/123/edit');
    expect(getProjectEditUrl('abc')).toBe('/projects/abc/edit');
  });
});

describe('doesDataNeedToBeRefreshed', () => {
  it('should return false if list is empty', () => {
    expect(doesDataNeedToBeRefreshed([])).toBe(false);
  });

  it('should return true if an entry has status Pending', () => {
    const projects = generateMockProjects(2);
    projects[0].status = ProjectStatus.PENDING;
    expect(doesDataNeedToBeRefreshed(projects)).toBe(true);
  });
  it('should return true if an entry has status Deleting', () => {
    const projects = generateMockProjects(2);
    projects[0].status = ProjectStatus.DELETING;
    expect(doesDataNeedToBeRefreshed(projects)).toBe(true);
  });

  it('should return false if no entry has status Pending or Deleting', () => {
    const projects = generateMockProjects(1);
    projects[0].status = ProjectStatus.READY;
    expect(doesDataNeedToBeRefreshed(projects)).toBe(false);
  });
});
