// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export type ApiKey = {
  id: string;
  projectId: string;
  displayName: string;
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

export type ApiKeyMetricsDataPoint = {
  date: string;
  [serviceId: string]: number | string;
};

export type ApiKeyMetrics = {
  stats: {
    totalRequests: number;
    successfulRequests: number;
    failedRequests: number;
    totalTokens: number;
    linkedDeployments: number;
  };
  services: string[];
  requestsOverTime: {
    total: ApiKeyMetricsDataPoint[];
    successful: ApiKeyMetricsDataPoint[];
    failed: ApiKeyMetricsDataPoint[];
  };
  tokensOverTime: {
    total: ApiKeyMetricsDataPoint[];
    input: ApiKeyMetricsDataPoint[];
    output: ApiKeyMetricsDataPoint[];
  };
};
