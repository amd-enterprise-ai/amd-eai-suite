// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select as SelectBase, SelectItem } from '@heroui/react';

export type {
  SelectProps,
  SelectItemProps,
  Selection,
} from '@heroui/react';

type SelectWithCompound = typeof SelectBase & {
  Item: typeof SelectItem;
};

const Select = SelectBase as SelectWithCompound;
Select.Item = SelectItem;

export { Select, SelectItem };
