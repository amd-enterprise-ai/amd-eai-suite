// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
// DRAFT
// This schema is a draft and is subject to change.
import { AllocatedResources, Workload } from '@/types/workloads';

import {
  CatalogItemCategory,
  CatalogItemEndpoint,
  CatalogItemType,
  CatalogUsageScope,
  InputFieldType,
  InputValueType,
  OutputType,
} from './enums/catalog';
import { WorkloadStatus } from './enums/workloads';

export interface CatalogItem {
  id: string;
  name: string;
  slug: string;
  displayName: string;
  description?: string;
  longDescription: string;
  type: CatalogItemType;
  category: CatalogItemCategory;
  createdAt: string;
  tags?: string[];
  featuredImage?: string;
  requiredResources?: RequiredResources;
  available?: boolean;
  externalUrl?: string;
  workloadsCount: number;
  workloads: Workload[];
  allocatedResources?: AllocatedResources;
  signature?: CatalogItemSignature;
  usageScope?: CatalogUsageScope;
}

export interface CatalogItemSignature {
  image: string;
}

export interface CatalogTableItem extends CatalogItem {
  allocatedResources?: AllocatedResources;
  status?: WorkloadStatus;
  outputs?: string[];
}

export interface RequiredResources {
  gpuCount?: number;
  gpuMemory?: number;
  cpuCoreCount?: number;
  systemMemory?: number;
}

export interface CatalogItemInput {
  label: string;
  name: string;
  type: InputValueType;
  required?: boolean;
  description?: string;
  options?: string[];
  minimum?: number;
  fieldType?: InputFieldType;
}

export interface CatalogItemOutput {
  name: string;
  type: OutputType;
  description?: string;
}

export interface CatalogItemDeployment {
  // Used for selecting the deployment endpoint
  type: CatalogItemEndpoint;
  template: string;
  // Used for deployment payload
  displayName?: string;
  gpus: number;
  memoryPerGpu: number;
  cpuPerGpu: number;
  image?: string;
  imagePullSecrets?: string[];
  replicas?: number;
}
