// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ApiKey } from '@/types/api-keys';

export const generateMockApiKeys = (count: number): ApiKey[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: `api-key-${i + 1}`,
    projectId: 'project-1',
    name: `API Key ${i + 1}`,
    truncatedKey: `sk_test_••••••••••••${(i + 1).toString().padStart(4, '0')}`,
    createdAt: new Date(2024, 0, i + 1).toISOString(),
    createdBy: `user${i + 1}@example.com`,
    expiresAt: i % 2 === 0 ? new Date(2025, 0, i + 1).toISOString() : undefined,
  }));
};

export const generateMockApiKey = (overrides?: Partial<ApiKey>): ApiKey => ({
  id: 'api-key-1',
  projectId: 'project-1',
  name: 'Test API Key',
  truncatedKey: 'sk_test_••••••••••••1234',
  createdAt: '2024-01-01T00:00:00Z',
  createdBy: 'test@example.com',
  expiresAt: '2025-01-01T00:00:00Z',
  ...overrides,
});

export const generateMockApiKeyResponse = () => ({
  apiKeys: generateMockApiKeys(3),
});

export const generateMockCreateApiKeyData = () => ({
  name: 'New API Key',
});

export const generateMockFullApiKey = (
  overrides?: Partial<ApiKey>,
): ApiKey => ({
  id: 'api-key-new',
  projectId: 'project-1',
  name: 'New API Key',
  truncatedKey: 'sk_live_abcdef1234567890abcdef1234567890',
  createdAt: '2024-01-01T00:00:00Z',
  createdBy: 'test@example.com',
  expiresAt: undefined,
  ...overrides,
});
