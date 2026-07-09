// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { IconChartBar, IconFolder, IconUsers } from '@tabler/icons-react';

import { SidebarItem } from '@amdenterpriseai/types';

import { MobileMenu } from '../src/Navigation/MobileMenu';

export default { title: 'Navigation/MobileMenu' } satisfies StoryDefault;

// Ladle has no i18n provider, so `t(stringKey)` falls back to the key itself.
// Using human-readable labels here keeps the story legible instead of showing
// raw keys like `pages.dashboard.title`.
const menuItems: SidebarItem[] = [
  {
    href: '/dashboard',
    stringKey: 'Dashboard',
    icon: <IconChartBar size={16} stroke={2} />,
  },
  {
    href: '/projects',
    stringKey: 'Projects',
    icon: <IconFolder size={16} stroke={2} />,
  },
  {
    href: '/users',
    stringKey: 'Users',
    icon: <IconUsers size={16} stroke={2} />,
    subItems: [
      { href: '/users/active', stringKey: 'Active Users' },
      { href: '/users/inactive', stringKey: 'Inactive Users' },
    ],
  },
];

// MobileMenu owns its open/close state internally, so a single story exercises
// both the closed (hamburger) state and the open drawer: press the hamburger to
// toggle the overlay listing the nav items (including nested sub-items).
export const Default: Story = () => (
  <div className="relative h-96 w-full max-w-sm border border-default-200 p-4">
    <MobileMenu menuItems={menuItems} />
    <p className="mt-4 text-sm text-default-500">
      Press the hamburger to open the navigation drawer.
    </p>
  </div>
);

export const WithProjectPrefix: Story = () => (
  <div className="relative h-96 w-full max-w-sm border border-default-200 p-4">
    <MobileMenu menuItems={menuItems} projectPrefix="my-project" />
    <p className="mt-4 text-sm text-default-500">
      Items navigate within the &quot;my-project&quot; prefix.
    </p>
  </div>
);
