// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export interface SidebarItem {
  href: string;
  stringKey: string;
  icon?: React.ReactElement;
  subItems?: SidebarItem[];
}

export type PageBreadcrumbItem = {
  title: string;
  href?: string;
};

export type PageBreadcrumbs = PageBreadcrumbItem[];
