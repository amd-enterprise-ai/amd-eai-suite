// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen, waitFor } from '@testing-library/react';

import { fetchOrganization } from '@/services/app';

import { Organization } from '@amdenterpriseai/types';

import { InviteUserButton } from '@/components/features/users/InviteUserButton';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';

vi.mock('@/services/app', () => ({
  fetchOrganization: vi.fn(),
}));

const mockUseAccessControl = vi.fn();
vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: () => mockUseAccessControl(),
}));

const mockFullOrganization: Organization = {
  idpLinked: false,
  smtpEnabled: true,
};

describe('InviteUserButton', () => {
  const mockFetchOrg = fetchOrganization as Mock;

  beforeEach(() => {
    mockFetchOrg.mockClear();
    mockUseAccessControl.mockReturnValue({
      isInviteEnabled: true,
      isAdministrator: true,
      isRoleManagementEnabled: true,
      smtpEnabled: true,
      isTempPasswordRequired: false,
    });
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
    mockUseAccessControl.mockReturnValue({
      isInviteEnabled: false,
      isAdministrator: true,
      isRoleManagementEnabled: true,
      smtpEnabled: false,
      isTempPasswordRequired: false,
    });
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
    mockUseAccessControl.mockReturnValue({
      isInviteEnabled: false,
      isAdministrator: true,
      isRoleManagementEnabled: true,
      smtpEnabled: true,
      isTempPasswordRequired: false,
    });
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
    mockUseAccessControl.mockReturnValue({
      isInviteEnabled: false,
      isAdministrator: true,
      isRoleManagementEnabled: true,
      smtpEnabled: false,
      isTempPasswordRequired: false,
    });
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
