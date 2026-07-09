// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tab as TabBase, Tabs as TabsBase } from '@heroui/react';
import type { ComponentProps } from 'react';

type TabsWithCompound = typeof TabsBase & {
  Tab: typeof TabBase;
};

const Tabs = TabsBase as TabsWithCompound;
Tabs.Tab = TabBase;

export { Tabs, TabBase as Tab };
export type TabsProps = ComponentProps<typeof TabsBase>;
export type TabItemProps = ComponentProps<typeof TabBase>;
