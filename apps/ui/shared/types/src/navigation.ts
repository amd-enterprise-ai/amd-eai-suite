// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { UserRole } from './enums/user-roles';

export interface SidebarItem {
  href: string;
  stringKey: string;
  icon?: React.ReactElement;
  subItems?: SidebarItem[];
  visibilityByRole?: Set<UserRole>;
}

export type PageBreadcrumbItem = {
  title: string;
  href?: string;
};

export type PageBreadcrumbs = PageBreadcrumbItem[];
