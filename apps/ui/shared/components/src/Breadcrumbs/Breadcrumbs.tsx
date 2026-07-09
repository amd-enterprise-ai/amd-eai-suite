// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { BreadcrumbItem, Breadcrumbs as BreadcrumbsBase } from '@heroui/react';

export type { BreadcrumbItemProps, BreadcrumbsProps } from '@heroui/react';

type BreadcrumbsWithCompound = typeof BreadcrumbsBase & {
  Item: typeof BreadcrumbItem;
};

const Breadcrumbs = BreadcrumbsBase as BreadcrumbsWithCompound;
Breadcrumbs.Item = BreadcrumbItem;

export { Breadcrumbs, BreadcrumbItem };
