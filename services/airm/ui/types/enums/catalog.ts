// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum CatalogItemCategory {
  TRAINING = 'training',
  INFERENCE = 'inference',
  DEVELOPMENT = 'development',
  MONITORING = 'monitoring',
}

export enum CatalogItemType {
  MODEL_DOWNLOAD = 'MODEL_DOWNLOAD',
  INFERENCE = 'INFERENCE',
  FINE_TUNING = 'FINE_TUNING',
  WORKSPACE = 'WORKSPACE',
}

export enum CatalogItemEndpoint {
  MODEL_DOWNLOAD = 'download',
  INFERENCE = 'deploy',
  FINE_TUNING = 'finetune',
  WORKSPACE = 'workspaces',
}

// Map CatalogItemTypes to corresponding endpoints
export const catalogItemTypeToEndpoint: Record<
  CatalogItemType,
  CatalogItemEndpoint
> = {
  [CatalogItemType.MODEL_DOWNLOAD]: CatalogItemEndpoint.MODEL_DOWNLOAD,
  [CatalogItemType.INFERENCE]: CatalogItemEndpoint.INFERENCE,
  [CatalogItemType.FINE_TUNING]: CatalogItemEndpoint.FINE_TUNING,
  [CatalogItemType.WORKSPACE]: CatalogItemEndpoint.WORKSPACE,
};

export enum InputValueType {
  STRING = 'string',
  INTEGER = 'integer',
  FLOAT = 'float',
  BOOLEAN = 'boolean',
  ARRAY = 'array',
  OBJECT = 'object',
  FILE = 'file',
}

export enum InputFieldType {
  TEXT = 'text',
  NUMBER = 'number',
  SELECT = 'select',
  CHECKBOX = 'checkbox',
  RADIO = 'radio',
  FILE = 'file',
  TEXTAREA = 'textarea',
  MULTISELECT = 'multiselect',
  TOGGLE = 'toggle',
  DATE = 'date',
  SLIDER = 'slider',
}

export enum OutputType {
  STRING = 'string',
  INTEGER = 'integer',
  FLOAT = 'float',
  BOOLEAN = 'boolean',
  ARRAY = 'array',
  OBJECT = 'object',
  FILE = 'file',
}

export enum CatalogUsageScope {
  USER = 'user',
  PROJECT = 'project',
}
