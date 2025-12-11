// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export type ApiKey = {
  id: string;
  projectId: string;
  name: string;
  truncatedKey: string;
  createdAt: string;
  createdBy: string;
  expiresAt?: string | null;
};

export type ApiKeyWithFullKey = ApiKey & {
  ttl: string | null;
  renewable: boolean;
  numUses: number;
  fullKey: string;
};

export type ApiKeyDetails = ApiKey & {
  ttl: string | null;
  renewable: boolean;
  numUses: number;
  groups: string[];
  entityId?: string;
  meta?: Record<string, unknown>;
};

export type ApiKeysResponse = {
  data: ApiKey[];
};
