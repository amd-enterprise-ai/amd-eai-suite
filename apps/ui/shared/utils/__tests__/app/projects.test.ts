// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect } from 'vitest';
import {
  getProjectDashboardUrl,
  getProjectEditUrl,
  getCandidateUsersForProject,
  getCandidateInvitedUsersForProject,
  doesProjectDataNeedToBeRefreshed,
} from '@amdenterpriseai/utils/app';
import { generateMockProjectWithMembers } from '@/__mocks__/utils/project-mock';
import { ProjectStatus } from '@amdenterpriseai/types';
import { InvitedUser, User } from '@amdenterpriseai/types';

describe('getProjectDashboardUrl', () => {
  it('should return correct dashboard URL', () => {
    expect(getProjectDashboardUrl('123')).toBe('/projects/123');
  });

  it('should handle string IDs with special characters', () => {
    expect(getProjectDashboardUrl('proj-abc-123')).toBe(
      '/projects/proj-abc-123',
    );
  });
});

describe('getProjectEditUrl', () => {
  it('should return correct edit URL', () => {
    expect(getProjectEditUrl('123')).toBe('/projects/123/edit');
  });

  it('should handle string IDs with special characters', () => {
    expect(getProjectEditUrl('proj-abc-123')).toBe(
      '/projects/proj-abc-123/edit',
    );
  });
});

describe('getCandidateUsersForProject', () => {
  it('should return empty array when allUsers is undefined', () => {
    const project = generateMockProjectWithMembers(1, 0);
    const result = getCandidateUsersForProject(project, undefined);
    expect(result).toEqual([]);
  });

  it('should filter out users already in project', () => {
    const project = generateMockProjectWithMembers(2, 0);
    const allUsers: User[] = [
      ...project.users,
      {
        id: '100',
        firstName: 'New',
        lastName: 'User',
        role: 'Team Member',
        email: 'new@example.com',
      },
    ];

    const result = getCandidateUsersForProject(project, allUsers);
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('100');
  });

  it('should sort candidate users by email', () => {
    const project = generateMockProjectWithMembers(1, 0);
    const allUsers: User[] = [
      ...project.users,
      {
        id: '100',
        firstName: 'Zebra',
        lastName: 'User',
        role: 'Team Member',
        email: 'z@example.com',
      },
      {
        id: '101',
        firstName: 'Alpha',
        lastName: 'User',
        role: 'Team Member',
        email: 'a@example.com',
      },
    ];

    const result = getCandidateUsersForProject(project, allUsers);
    expect(result).toHaveLength(2);
    expect(result[0].email).toBe('a@example.com');
    expect(result[1].email).toBe('z@example.com');
  });

  it('should return all users when project has no users', () => {
    const project = generateMockProjectWithMembers(0, 0);
    const allUsers: User[] = [
      {
        id: '100',
        firstName: 'User',
        lastName: 'One',
        role: 'Team Member',
        email: 'user1@example.com',
      },
      {
        id: '101',
        firstName: 'User',
        lastName: 'Two',
        role: 'Team Member',
        email: 'user2@example.com',
      },
    ];

    const result = getCandidateUsersForProject(project, allUsers);
    expect(result).toHaveLength(2);
  });
});

describe('getCandidateInvitedUsersForProject', () => {
  it('should return empty array when allInvitedUsers is undefined', () => {
    const project = generateMockProjectWithMembers(0, 1);
    const result = getCandidateInvitedUsersForProject(project, undefined);
    expect(result).toEqual([]);
  });

  it('should filter out invited users already in project', () => {
    const project = generateMockProjectWithMembers(0, 2);
    const allInvitedUsers: InvitedUser[] = [
      ...project.invitedUsers,
      {
        id: 'i100',
        email: 'new-invited@example.com',
        role: 'Team Member',
      },
    ];

    const result = getCandidateInvitedUsersForProject(project, allInvitedUsers);
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('i100');
  });

  it('should sort candidate invited users by email', () => {
    const project = generateMockProjectWithMembers(0, 1);
    const allInvitedUsers: InvitedUser[] = [
      ...project.invitedUsers,
      { id: 'i100', email: 'z@example.com', role: 'Team Member' },
      { id: 'i101', email: 'a@example.com', role: 'Team Member' },
    ];

    const result = getCandidateInvitedUsersForProject(project, allInvitedUsers);
    expect(result).toHaveLength(2);
    expect(result[0].email).toBe('a@example.com');
    expect(result[1].email).toBe('z@example.com');
  });

  it('should return all invited users when project has no invited users', () => {
    const project = generateMockProjectWithMembers(0, 0);
    const allInvitedUsers: InvitedUser[] = [
      { id: 'i100', email: 'invited1@example.com', role: 'Team Member' },
      { id: 'i101', email: 'invited2@example.com', role: 'Team Member' },
    ];

    const result = getCandidateInvitedUsersForProject(project, allInvitedUsers);
    expect(result).toHaveLength(2);
  });
});

describe('doesProjectDataNeedToBeRefreshed', () => {
  it('should return false if list is empty', () => {
    expect(doesProjectDataNeedToBeRefreshed([])).toBe(false);
  });

  it('should return true if a project has PENDING status', () => {
    const projects = generateMockProjectWithMembers(0, 0);
    projects.status = ProjectStatus.PENDING;
    expect(doesProjectDataNeedToBeRefreshed([projects])).toBe(true);
  });

  it('should return true if a project has DELETING status', () => {
    const projects = generateMockProjectWithMembers(0, 0);
    projects.status = ProjectStatus.DELETING;
    expect(doesProjectDataNeedToBeRefreshed([projects])).toBe(true);
  });

  it('should return false if no project has PENDING or DELETING status', () => {
    const projects = generateMockProjectWithMembers(0, 0);
    projects.status = ProjectStatus.READY;
    expect(doesProjectDataNeedToBeRefreshed([projects])).toBe(false);
  });

  it('should return true if at least one project needs refresh', () => {
    const project1 = generateMockProjectWithMembers(0, 0);
    project1.status = ProjectStatus.READY;
    const project2 = generateMockProjectWithMembers(0, 0);
    project2.status = ProjectStatus.PENDING;
    expect(doesProjectDataNeedToBeRefreshed([project1, project2])).toBe(true);
  });
});
