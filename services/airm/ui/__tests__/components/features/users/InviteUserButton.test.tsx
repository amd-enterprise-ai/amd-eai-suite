// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen, waitFor } from '@testing-library/react';

import { fetchOrganization } from '@/services/app/organizations';

import { Organization } from '@/types/organization';

import { InviteUserButton } from '@/components/features/users/InviteUserButton';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';
import { UserRole } from '@/types/enums/user-roles';

vi.mock('@/services/app/organizations', () => ({
  fetchOrganization: vi.fn(),
}));

// Mock useSession locally
vi.mock('next-auth/react', () => ({
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
  useSession: () => ({
    data: {
      accessToken: 'mock-token',
      user: {
        roles: UserRole.PLATFORM_ADMIN,
      },
    },
    status: 'authenticated',
  }),
}));

const mockFullOrganization: Organization = {
  id: 'org1',
  name: 'Test Org',
  domains: ['example.com'],
  idpLinked: false,
  smtpEnabled: true,
};

describe('InviteUserButton', () => {
  const mockFetchOrg = fetchOrganization as Mock;

  beforeEach(() => {
    mockFetchOrg.mockClear();
    // If your QueryClientWrapper or global setup doesn't clear queries,
    // you might need to clear the query cache here too.
    // e.g., queryClient.clear(); if queryClient is accessible here.
  });

  it('shows button when SMTP is enabled', async () => {
    mockFetchOrg.mockResolvedValue({
      ...mockFullOrganization,
      idpLinked: false,
      smtpEnabled: true, // This should make the button show
    });
    await act(async () => {
      render(<InviteUserButton onClick={() => {}} label="Invite User" />, {
        wrapper,
      });
    });

    await waitFor(() => {
      const button = screen.queryByRole('button');
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();
    });
  });

  it('hides button when SMTP is disabled and IDP is not linked', async () => {
    mockFetchOrg.mockResolvedValue({
      ...mockFullOrganization,
      idpLinked: false,
      smtpEnabled: false,
    });
    await act(async () => {
      render(<InviteUserButton onClick={() => {}} label="Invite User" />, {
        wrapper,
      });
    });

    await waitFor(() => {
      const button = screen.queryByRole('button');
      expect(button).not.toBeInTheDocument();
    });
  });

  it('hides button when IDP is linked even if SMTP is enabled', async () => {
    mockFetchOrg.mockResolvedValue({
      ...mockFullOrganization,
      idpLinked: true,
      smtpEnabled: true,
    });
    await act(async () => {
      render(<InviteUserButton onClick={() => {}} label="Invite User" />, {
        wrapper,
      });
    });

    await waitFor(() => {
      const button = screen.queryByRole('button');
      expect(button).not.toBeInTheDocument();
    });
  });

  it('hides button when both IDP is linked and SMTP is disabled', async () => {
    mockFetchOrg.mockResolvedValue({
      ...mockFullOrganization,
      idpLinked: true,
      smtpEnabled: false,
    });
    await act(async () => {
      render(<InviteUserButton onClick={() => {}} label="Invite User" />, {
        wrapper,
      });
    });

    await waitFor(() => {
      const button = screen.queryByRole('button');
      expect(button).not.toBeInTheDocument();
    });
  });
});
