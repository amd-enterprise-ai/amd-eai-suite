// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Popover as HeroPopover,
  PopoverContent as HeroPopoverContent,
  PopoverTrigger as HeroPopoverTrigger,
  type PopoverContentProps,
  type PopoverProps,
  type PopoverTriggerProps,
} from '@heroui/react';

type PopoverCompound = typeof HeroPopover & {
  Trigger: typeof HeroPopoverTrigger;
  Content: typeof HeroPopoverContent;
};

const Popover = HeroPopover as PopoverCompound;
Popover.Trigger = HeroPopoverTrigger;
Popover.Content = HeroPopoverContent;

export {
  Popover,
  HeroPopoverTrigger as PopoverTrigger,
  HeroPopoverContent as PopoverContent,
};
export type { PopoverProps, PopoverContentProps, PopoverTriggerProps };
