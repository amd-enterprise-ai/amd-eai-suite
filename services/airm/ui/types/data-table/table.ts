// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ReactNode } from 'react';

import { SortDirection } from '../enums/sort-direction';
import { FilterParams } from './server-collection';

export type TableColumn<T> = {
  key: T;
  sortable?: boolean;
  className?: string;
  hasDescription?: boolean;
  sortDirection?: SortDirection;
  width?: number;
  maxWidth?: number;
  minWidth?: number;
};

export type TableColumns<T> = Array<TableColumn<T>>;

export type ActionItem<T> = {
  key: string;
  className?: string;
  onPress: (item: T) => void;
  startContent?: ReactNode;
  color?: string;
  label: string;
  isDisabled?: boolean | ((item: T) => boolean);
};
