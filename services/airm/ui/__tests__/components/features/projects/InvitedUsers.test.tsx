// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { QueryClient } from '@tanstack/react-query';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';

import { fetchOrganization } from '@/services/app/organizations';
import { fetchProjects } from '@/services/app/projects';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';

import { Organization } from '@/types/organization';
import { ProjectWithMembers } from '@/types/projects';

import { InvitedUsers } from '@/components/features/projects';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';

vi.mock('@/services/app/projects', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchProjects: vi.fn(),
  };
});

vi.mock('@/services/app/organizations', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchOrganization: vi.fn(),
  };
});

const mockProject: ProjectWithMembers = {
  ...generateMockProjects(1)[0],
  users: [
    {
      id: 'user1',
      firstName: 'User 1',
      lastName: 'Last 1',
      role: 'Team Member',
      email: 'user1@example.com',
    },
  ],
  invitedUsers: [
    {
      id: 'user2',
      email: 'user2@example.com',
      role: 'Platform Administrator',
    },
    {
      id: 'user3',
      email: 'user3@example.com',
      role: 'Team Member',
    },
  ],
};

const mockFullOrganization: Organization = {
  id: 'org1',
  name: 'Test Org',
  domains: ['example.com'],
  idpLinked: false,
  smtpEnabled: false,
};

describe('InvitedUsers', () => {
  const mockFetchProjects = fetchProjects as Mock;

  beforeEach(() => {
    mockFetchProjects.mockClear();
  });

  it('renders the component with Invited Users', () => {
    act(() => {
      render(<InvitedUsers project={mockProject} />, { wrapper });
    });
    expect(
      screen.getByText('settings.membersAndInvitedUsers.invitedUsers.title'),
    ).toBeInTheDocument();
    expect(screen.getByText('user2@example.com')).toBeInTheDocument();
    expect(screen.getByText('user3@example.com')).toBeInTheDocument();
  });

  it('renders the component without Invited Users', () => {
    act(() => {
      render(<InvitedUsers project={{ ...mockProject, invitedUsers: [] }} />, {
        wrapper,
      });
    });
    expect(
      screen.getByText('settings.membersAndInvitedUsers.invitedUsers.title'),
    ).toBeInTheDocument();
  });

  it('Able to open the invite user modal with the project pre-selected', async () => {
    mockFetchProjects.mockResolvedValue({
      projects: [mockProject],
    });
    await act(async () => {
      render(<InvitedUsers project={mockProject} />, { wrapper });
    });
    const addButton = screen.getByLabelText(
      'settings.membersAndInvitedUsers.invitedUsers.actions.add',
    ) as HTMLInputElement;

    await waitFor(() => expect(mockFetchProjects).toBeCalled());

    await fireEvent.click(addButton);

    const { getByText } = within(screen.getByTestId('project-select'));
    expect(getByText('project-1')).toBeInTheDocument();
  });
});

describe('Invite User button enabled/disabled state', () => {
  const mockFetchOrg = fetchOrganization as Mock;
  let queryClient: QueryClient;

  it('disables the Invite User button if org has identity provider', async () => {
    mockFetchOrg.mockResolvedValue({
      ...mockFullOrganization,
      idpLinked: true,
    });
    await act(() => {
      render(<InvitedUsers project={mockProject} />, { wrapper });
    });

    const inviteButton = screen.getByLabelText(
      'settings.membersAndInvitedUsers.invitedUsers.actions.add',
    ) as HTMLInputElement;
    await waitFor(() => {
      expect(inviteButton).toBeDisabled();
    });
  });

  it('enables the Invite User button if org does not have identity provider', async () => {
    mockFetchOrg.mockResolvedValue({
      ...mockFullOrganization,
      idpLinked: false,
    });
    await act(() => {
      render(<InvitedUsers project={mockProject} />, { wrapper });
    });
    const inviteButton = screen.getByLabelText(
      'settings.membersAndInvitedUsers.invitedUsers.actions.add',
    ) as HTMLInputElement;
    await waitFor(() => {
      expect(inviteButton).toBeEnabled();
    });
  });

  it('enables the Invite User button if identity provider info fails to load', async () => {
    mockFetchOrg.mockRejectedValue(new Error('API Error'));
    await act(() => {
      render(<InvitedUsers project={mockProject} />, { wrapper });
    });
    const inviteButton = screen.getByLabelText(
      'settings.membersAndInvitedUsers.invitedUsers.actions.add',
    ) as HTMLInputElement;
    await waitFor(() => {
      expect(inviteButton).toBeEnabled();
    });
  });
});
