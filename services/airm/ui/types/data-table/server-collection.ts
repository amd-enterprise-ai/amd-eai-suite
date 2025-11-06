// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { FilterOperator } from '../enums/server-collection';
import { SortDirection } from '../enums/sort-direction';

export type FilterParams<T> = {
  fields: (keyof T)[];
  operator?: FilterOperator; // Default to CONTAINS/EQ behaviour on services side if not defined.
  values: string[];
};

export type SortParams<T> = {
  field: keyof T;
  direction: SortDirection;
};

export type PaginationParams<T> = {
  page: number;
  page_size: number;
};

export type CollectionRequestParams<T> = {
  sort?: SortParams<T>[];
  filter?: FilterParams<T>[];
  page: number;
  pageSize: number;
};

export type ServerCollectionMetadata = {
  total: number;
  page: number;
  pageSize: number;
};

export type CustomSortFieldMapperConfig<
  T,
  K extends string | number | symbol,
> = {
  [key in K]?: { fields: (keyof T)[] };
};
