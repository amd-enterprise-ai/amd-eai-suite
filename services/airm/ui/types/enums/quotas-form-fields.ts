// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum QuotaAllocationEditFields {
  GPU = 'gpu',
  CPU = 'cpu',
  RAM = 'ram',
  DISK = 'disk',
}

export enum QuotaBasicFields {
  NAME = 'name',
  DESCRIPTION = 'description',
}

export type QuotaEditFields = QuotaBasicFields | QuotaAllocationEditFields;

export enum QuotaAddFields {
  NAME = 'name',
  DESCRIPTION = 'description',
  CLUSTER = 'cluster',
  PROJECT = 'project',
}

export enum QuotaFormGrouping {
  EDIT_QUOTA = 'editQuota',
  ACCORDION = 'accordion',
  BASIC_INFO = 'basicInfo',
  GUARANTEED_QUOTA = 'guaranteedQuota',
  GUARANTEED_QUOTA_INFO = 'guaranteedQuotaInfo',
  GUARANTEED_QUOTA_SETTINGS = 'guaranteedQuotaSettings',
}
