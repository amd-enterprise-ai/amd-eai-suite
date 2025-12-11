// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Drawer, DrawerBody, DrawerContent, DrawerHeader } from '@heroui/react';

import { CloseButton } from '@/components/shared/Buttons';
import { BACKDROP, CLASSES, MOTION_PROPS } from './constants';
import { PropsWithChildren } from 'react';

interface Props {
  isOpen?: boolean;
  title: string;
  onOpenChange?: () => void;
}

export const DrawerDisplay = ({
  isOpen,
  onOpenChange,
  title,
  children,
}: PropsWithChildren<Props>) => {
  return (
    <Drawer
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      motionProps={MOTION_PROPS}
      backdrop={BACKDROP}
      closeButton={<CloseButton />}
      classNames={CLASSES}
    >
      <DrawerContent>
        <DrawerHeader>{title}</DrawerHeader>
        <DrawerBody className="w-full">{children}</DrawerBody>
      </DrawerContent>
    </Drawer>
  );
};

export default DrawerDisplay;
