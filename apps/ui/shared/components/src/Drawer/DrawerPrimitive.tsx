// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Drawer as HeroDrawer,
  DrawerBody as HeroDrawerBody,
  DrawerContent as HeroDrawerContent,
  DrawerFooter as HeroDrawerFooter,
  DrawerHeader as HeroDrawerHeader,
} from '@heroui/react';

export const DrawerBody = HeroDrawerBody;
export const DrawerContent = HeroDrawerContent;
export const DrawerFooter = HeroDrawerFooter;
export const DrawerHeader = HeroDrawerHeader;

type DrawerCompound = typeof HeroDrawer & {
  Body: typeof HeroDrawerBody;
  Content: typeof HeroDrawerContent;
  Footer: typeof HeroDrawerFooter;
  Header: typeof HeroDrawerHeader;
};

export const DrawerPrimitive = HeroDrawer as DrawerCompound;
DrawerPrimitive.Body = DrawerBody;
DrawerPrimitive.Content = DrawerContent;
DrawerPrimitive.Footer = DrawerFooter;
DrawerPrimitive.Header = DrawerHeader;
