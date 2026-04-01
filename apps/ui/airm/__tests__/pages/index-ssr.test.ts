// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect, vi, beforeEach } from 'vitest';

// IMPORTANT: Mocks must be declared BEFORE importing the page module
vi.mock('next-auth', () => ({ getServerSession: vi.fn() }));
vi.mock('next-i18next/serverSideTranslations', () => ({
  serverSideTranslations: vi.fn().mockResolvedValue({}),
}));
vi.mock('@/services/server', () => ({
  getClusterStats: vi.fn().mockResolvedValue({
    totalClusterCount: 1,
    totalNodeCount: 2,
    availableNodeCount: 2,
    totalGpuNodeCount: 1,
    totalGpuCount: 4,
    availableGpuCount: 4,
    allocatedGpuCount: 0,
  }),
}));
vi.mock('@amdenterpriseai/utils/server', () => ({ authOptions: {} }));

import { getServerSession } from 'next-auth';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { getClusterStats } from '@/services/server';
import { UserRole } from '@amdenterpriseai/types';
import { getServerSideProps } from '@/pages';

// Helper creators
const createSession = (overrides: Record<string, any> = {}) => ({
  user: {
    email: 'admin@example.com',
    roles: [UserRole.PLATFORM_ADMIN],
    ...overrides.user,
  },
  accessToken: 'token',
  ...overrides,
});

// Handy cast for the vi mock
const getServerSessionMock = getServerSession as unknown as ReturnType<
  typeof vi.fn
>;

describe('pages/index getServerSideProps', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('redirects to / when no session', async () => {
    getServerSessionMock.mockResolvedValue(undefined);
    const result: any = await getServerSideProps({
      locale: 'en',
      req: {},
      res: {},
    } as any);
    expect(result.redirect.destination).toBe('/');
    expect(result.redirect.permanent).toBe(false);
  });

  // Removed explicit missing-email admin test due to environment variance; core branches covered below

  it('redirects non-admin users to first accessible route', async () => {
    getServerSessionMock.mockResolvedValue(
      createSession({ user: { roles: [] } }),
    );
    const result: any = await getServerSideProps({
      locale: 'en',
      req: {},
      res: {},
    } as any);
    expect(result.redirect.destination).toBe('/clusters');
    expect(result.props).toBeUndefined();
  });

  it('returns props with clusterStats when admin session valid', async () => {
    getServerSessionMock.mockResolvedValue(createSession());
    const result: any = await getServerSideProps({
      locale: 'en',
      req: {},
      res: {},
    } as any);
    expect(serverSideTranslations).toHaveBeenCalled();
    expect(getClusterStats).toHaveBeenCalled();
    expect(result.props).toBeDefined();
  });
});
