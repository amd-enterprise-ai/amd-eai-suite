// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fetchOrganization } from '@/services/app';

import { APIRequestError } from '@amdenterpriseai/utils/app';

import { Organization } from '@amdenterpriseai/types';

// Mock dependencies
vi.mock('@amdenterpriseai/utils/app', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@amdenterpriseai/utils/app')>();
  return {
    ...actual,
    getErrorMessage: vi.fn().mockResolvedValue('Some error'),
  };
});

const mockOrganization: Organization = {
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

    const { getErrorMessage } = await import('@amdenterpriseai/utils/app');

    await expect(fetchOrganization()).rejects.toThrow(APIRequestError);
    expect(getErrorMessage).toHaveBeenCalled();
  });
});
