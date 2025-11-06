// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ClusterBasicInfo } from './clusters';
import { QuotaResource, QuotaStatus } from './enums/quotas';
import {
  QuotaAddFields,
  QuotaAllocationEditFields,
  QuotaBasicFields,
  QuotaEditFields,
} from './enums/quotas-form-fields';
import { Project } from './projects';

export type QuotaResourceType = {
  [QuotaResource.GPU]: number;
  [QuotaResource.CPU]: number;
  [QuotaResource.RAM]: number;
  [QuotaResource.DISK]: number;
};

// Create a union type that combines the values of both enums
export type QuotaField = QuotaResource | QuotaEditFields;

export type Quota = {
  status: QuotaStatus;
  statusReason?: string;
} & QuotaResourceType;

export type UpdateQuotaRequest = {
  cpu_milli_cores: number;
  gpu_count: number;
  memory_bytes: number;
  ephemeral_storage_bytes: number;
};

export type QuotasResponse = {
  quotas: Quota[];
};

export type QuotaBase = {
  cpuMilliCores: number;
  gpuCount: number;
  memoryBytes: number;
  ephemeralStorageBytes: number;
};

export type QuotaAllocationFormData = {
  [QuotaAllocationEditFields.CPU]: number;
  [QuotaAllocationEditFields.GPU]: number;
  [QuotaAllocationEditFields.RAM]: number;
  [QuotaAllocationEditFields.DISK]: number;
};

export type QuotaFormData = {
  [QuotaBasicFields.NAME]: string;
  [QuotaBasicFields.DESCRIPTION]: string;
} & QuotaAllocationFormData;

export type CreateQuotaFormData = {
  [QuotaAddFields.NAME]: string;
  [QuotaAddFields.DESCRIPTION]?: string;
  [QuotaAddFields.PROJECT]: string;
  [QuotaAddFields.CLUSTER]: string;
};
