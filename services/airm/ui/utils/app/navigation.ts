// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  IconAppWindow,
  IconChartBar,
  IconCheckupList,
  IconCpu,
  IconDatabase,
  IconFolderRoot,
  IconHammer,
  IconKey,
  IconMessage,
  IconServer,
  IconShieldLock,
  IconUsers,
} from '@tabler/icons-react';
import React from 'react';

import { SidebarItem } from '@/types/navigation';

export const airmMenuItems: SidebarItem[] = [
  {
    href: '/',
    stringKey: 'pages.dashboard.title',
    icon: React.createElement(IconChartBar, { size: 16, stroke: 2 }),
  },
  {
    href: '/clusters',
    stringKey: 'pages.clusters.title',
    icon: React.createElement(IconServer, { size: 16, stroke: 2 }),
  },
  {
    href: '/projects',
    stringKey: 'pages.projects.title',
    icon: React.createElement(IconCheckupList, { size: 16, stroke: 2 }),
  },
  {
    href: '/secrets',
    stringKey: 'pages.secrets.title',
    icon: React.createElement(IconShieldLock, { size: 16, stroke: 2 }),
  },
  {
    href: '/storages',
    stringKey: 'pages.storages.title',
    icon: React.createElement(IconFolderRoot, { size: 16, stroke: 2 }),
  },
  {
    href: '/users',
    stringKey: 'pages.users.title',
    icon: React.createElement(IconUsers, { size: 16, stroke: 2 }),
  },
];

export const aiWorkbenchMenuItems: SidebarItem[] = [
  {
    href: '/api-keys',
    stringKey: 'pages.apiKeys.title',
    icon: React.createElement(IconKey, { size: 16, stroke: 2 }),
  },
  {
    href: '/chat',
    stringKey: 'pages.chat.title',
    icon: React.createElement(IconMessage, { size: 16, stroke: 2 }),
  },
  {
    href: '/datasets',
    stringKey: 'pages.datasets.title',
    icon: React.createElement(IconDatabase, { size: 16, stroke: 2 }),
  },
  {
    href: '/models',
    stringKey: 'pages.models.title',
    icon: React.createElement(IconCpu, { size: 16, stroke: 2 }),
  },
  {
    href: '/workbench-secrets',
    stringKey: 'pages.workbenchSecrets.title',
    icon: React.createElement(IconShieldLock, { size: 16, stroke: 2 }),
  },
  {
    href: '/workloads',
    stringKey: 'pages.workloads.title',
    icon: React.createElement(IconHammer, { size: 16, stroke: 2 }),
  },
  {
    href: '/workspaces',
    stringKey: 'pages.workspaces.title',
    icon: React.createElement(IconAppWindow, { size: 16, stroke: 2 }),
  },
];

export const isMenuItemActive = (
  href: string,
  path: string | null,
): boolean => {
  if (!path) return false;

  // Special case for root path to avoid matching all paths
  if (href === '/') {
    return path === '/';
  }

  // Check if current path matches exactly or starts with the href
  return path === href || path.startsWith(href + '/');
};
