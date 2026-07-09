// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Listbox as ListboxBase,
  ListboxItem,
  ListboxSection,
} from '@heroui/react';

export type {
  ListboxItemProps,
  ListboxProps,
  ListboxSectionProps,
} from '@heroui/react';

type ListboxWithCompound = typeof ListboxBase & {
  Item: typeof ListboxItem;
  Section: typeof ListboxSection;
};

const Listbox = ListboxBase as ListboxWithCompound;
Listbox.Item = ListboxItem;
Listbox.Section = ListboxSection;

export { Listbox, ListboxItem, ListboxSection };
