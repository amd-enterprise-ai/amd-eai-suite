// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Dropdown as HeroDropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSection,
  DropdownTrigger,
  type DropdownItemProps,
  type DropdownProps,
} from '@heroui/react';

type DropdownWithSubComponents = typeof HeroDropdown & {
  Item: typeof DropdownItem;
  Menu: typeof DropdownMenu;
  Section: typeof DropdownSection;
  Trigger: typeof DropdownTrigger;
};

const Dropdown = HeroDropdown as DropdownWithSubComponents;
Dropdown.Item = DropdownItem;
Dropdown.Menu = DropdownMenu;
Dropdown.Section = DropdownSection;
Dropdown.Trigger = DropdownTrigger;

export {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSection,
  DropdownTrigger,
};
export type { DropdownItemProps, DropdownProps };
