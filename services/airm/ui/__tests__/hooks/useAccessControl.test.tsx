// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useSession } from 'next-auth/react';

import { useAccessControl } from '../../hooks/useAccessControl';
import { ProviderWrapper } from '../ProviderWrapper';
import {
  mockOrganization,
  mockOrganizationAccessDisabled,
  mockOrganizationIdpLinked,
  mockOrganizationIdpLinkedSmtpDisabled,
} from '../../__mocks__/services/app/organizations.data';

// Mock the organization service
vi.mock('../../services/app/organizations', () => ({
  fetchOrganization: vi.fn(),
}));

// Mock the useSession hook
vi.mock('next-auth/react', () => ({
  useSession: vi.fn(),
}));

import { fetchOrganization } from '../../services/app/organizations';

const mockedFetchOrganization = vi.mocked(fetchOrganization);
const mockUseSession = vi.mocked(useSession);

describe('useAccessControl', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default session mock
    mockUseSession.mockReturnValue({
      data: {
        user: {
          id: 'user1',
          email: 'test@example.com',
          roles: ['Team Member'],
        },
        accessToken: 'mock-token',
        expires: '2025-01-01',
      },
      status: 'authenticated',
    } as any);
  });

  describe('isRoleManagementEnabled', () => {
    it('should return true when SMTP is enabled and IDP is not linked', async () => {
      mockedFetchOrganization.mockResolvedValue(mockOrganization);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      await waitFor(() => {
        expect(result.current.isRoleManagementEnabled).toBe(true);
      });
    });

    it('should return false when IDP is linked (even if SMTP is enabled)', async () => {
      mockedFetchOrganization.mockResolvedValue(mockOrganizationIdpLinked);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      await waitFor(() => {
        expect(result.current.isRoleManagementEnabled).toBe(false);
      });
    });

    it('should return true when IDP is not linked (regardless of SMTP status)', async () => {
      mockedFetchOrganization.mockResolvedValue(mockOrganizationAccessDisabled);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      await waitFor(() => {
        expect(result.current.isRoleManagementEnabled).toBe(true);
      });
    });

    it('should return false when organization data is not available', () => {
      mockedFetchOrganization.mockResolvedValue(undefined as any);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      expect(result.current.isRoleManagementEnabled).toBe(false);
    });
  });

  describe('isInviteEnabled', () => {
    it('should return true when SMTP is enabled', async () => {
      mockedFetchOrganization.mockResolvedValue(mockOrganization);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      await waitFor(() => {
        expect(result.current.isInviteEnabled).toBe(true);
      });
    });

    it('should return false when SMTP is disabled', async () => {
      mockedFetchOrganization.mockResolvedValue(mockOrganizationAccessDisabled);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      await waitFor(() => {
        expect(result.current.isInviteEnabled).toBe(false);
      });
    });

    it('should return false when IDP is linked (even if SMTP is enabled)', async () => {
      mockedFetchOrganization.mockResolvedValue(mockOrganizationIdpLinked);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      await waitFor(() => {
        expect(result.current.isInviteEnabled).toBe(false);
      });
    });

    it('should return false when IDP is linked and SMTP is disabled', async () => {
      mockedFetchOrganization.mockResolvedValue(
        mockOrganizationIdpLinkedSmtpDisabled,
      );

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      await waitFor(() => {
        expect(result.current.isInviteEnabled).toBe(false);
      });
    });

    it('should return false when organization data is not available', () => {
      mockedFetchOrganization.mockResolvedValue(undefined as any);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      expect(result.current.isInviteEnabled).toBe(false);
    });
  });

  describe('isAdministrator', () => {
    it('should return true when user has Platform Administrator role', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: {
            id: 'admin1',
            email: 'admin@example.com',
            roles: ['Platform Administrator'],
          },
          accessToken: 'mock-token',
          expires: '2025-01-01',
        },
        status: 'authenticated',
      } as any);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      expect(result.current.isAdministrator).toBe(true);
    });

    it('should return false when user has Team Member role', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: {
            id: 'user1',
            email: 'user@example.com',
            roles: ['Team Member'],
          },
          accessToken: 'mock-token',
          expires: '2025-01-01',
        },
        status: 'authenticated',
      } as any);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      expect(result.current.isAdministrator).toBe(false);
    });

    it('should return false when user has no roles', () => {
      mockUseSession.mockReturnValue({
        data: {
          user: {
            id: 'user1',
            email: 'user@example.com',
            roles: [],
          },
          accessToken: 'mock-token',
          expires: '2025-01-01',
        },
        status: 'authenticated',
      } as any);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      expect(result.current.isAdministrator).toBe(false);
    });

    it('should return false when session data is not available', () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

      const { result } = renderHook(() => useAccessControl(), {
        wrapper: ProviderWrapper,
      });

      expect(result.current.isAdministrator).toBe(false);
    });
  });
});
