// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getCurrentUserOrganizationDetails } from '@/services/server/organizations';

import { Organization } from '@/types/organization';

describe('getCurrentUserOrganizationDetails', () => {
  const token = 'test-token';
  const apiUrl = 'https://api.example.com';
  const orgResponse = { id: '1', org_name: 'Test Org' };
  const orgCamel: Organization = {
    id: '1',
    name: 'Test Org',
    domains: [],
    idpLinked: false,
    smtpEnabled: false,
  };

  let fetchMock: ReturnType<typeof vi.fn>;
  let convertSnakeToCamelMock: ReturnType<typeof vi.fn>;
  let getErrorMessageMock: ReturnType<typeof vi.fn>;
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
    process.env.AIRM_API_SERVICE_URL = apiUrl;

    fetchMock = vi.fn();
    convertSnakeToCamelMock = vi.fn();
    getErrorMessageMock = vi.fn();

    global.fetch = fetchMock;
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it('should fetch organization details and return camel-cased organization', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(orgResponse),
    });
    convertSnakeToCamelMock.mockReturnValue(orgCamel);

    const result = await getCurrentUserOrganizationDetails(token);

    expect(fetchMock).toHaveBeenCalledWith(
      `${apiUrl}/v1/organization`,
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        }),
      }),
    );
    expect(result).toEqual({
      id: '1',
      orgName: 'Test Org',
    });
  });

  it('should throw error if response is not ok', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      json: vi.fn(),
    });
    getErrorMessageMock.mockResolvedValue('Unauthorized');

    await expect(getCurrentUserOrganizationDetails(token)).rejects.toThrow(
      /^Error fetching organization details/,
    );
    expect(console.error).toHaveBeenCalled();
  });

  it('should throw error if fetch throws', async () => {
    const error = new Error('Network error');
    fetchMock.mockRejectedValue(error);

    await expect(getCurrentUserOrganizationDetails(token)).rejects.toThrow(
      error,
    );
    expect(console.error).toHaveBeenCalled();
  });
});
