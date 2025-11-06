// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fetchOrganization } from '@/services/app/organizations';

import { APIRequestError } from '@/utils/app/errors';

import { Organization } from '@/types/organization';

// Mock dependencies
vi.mock('@/utils/app/api-helpers', () => ({
  getErrorMessage: vi.fn().mockResolvedValue('Some error'),
}));

const mockOrganization: Organization = {
  id: 'org-1',
  name: 'Test Org',
  domains: ['amd.com'],
  idpLinked: false,
  smtpEnabled: false,
};

describe('fetchOrganization', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('returns organization data when response is ok', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockOrganization),
    } as any);

    const result = await fetchOrganization();
    expect(result).toEqual(mockOrganization);
    expect(global.fetch).toHaveBeenCalledWith('/api/organization');
  });

  it('throws APIRequestError when response is not ok', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: vi.fn(),
    } as any);

    const { getErrorMessage } = await import('@/utils/app/api-helpers');

    await expect(fetchOrganization()).rejects.toThrow(APIRequestError);
    await expect(fetchOrganization()).rejects.toThrow(
      /Failed to fetch organization information/,
    );
    expect(getErrorMessage).toHaveBeenCalled();
  });
});
