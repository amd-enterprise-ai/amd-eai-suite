// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';
import {
  DrawerPrimitive,
  DrawerBody,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
} from '../../../src/Drawer';
import { ActionButton } from '../../../src/Buttons';

export default {
  title: 'Components/Drawer/DrawerPrimitive',
} satisfies StoryDefault;

type Placement = 'left' | 'right' | 'top' | 'bottom';
type Size = 'sm' | 'md' | 'lg' | 'xl' | 'full';

export const CompoundAPI: Story = () => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <>
      <ActionButton primary onPress={() => setIsOpen(true)}>
        Open Drawer
      </ActionButton>
      <DrawerPrimitive isOpen={isOpen} onOpenChange={() => setIsOpen(false)}>
        <DrawerPrimitive.Content>
          <DrawerPrimitive.Header>Compound API</DrawerPrimitive.Header>
          <DrawerPrimitive.Body>
            <p>This drawer uses the compound component pattern.</p>
          </DrawerPrimitive.Body>
          <DrawerPrimitive.Footer>
            <ActionButton secondary onPress={() => setIsOpen(false)}>
              Close
            </ActionButton>
          </DrawerPrimitive.Footer>
        </DrawerPrimitive.Content>
      </DrawerPrimitive>
    </>
  );
};

export const FlatAliases: Story = () => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <>
      <ActionButton primary onPress={() => setIsOpen(true)}>
        Open Drawer
      </ActionButton>
      <DrawerPrimitive isOpen={isOpen} onOpenChange={() => setIsOpen(false)}>
        <DrawerContent>
          <DrawerHeader>Flat Aliases</DrawerHeader>
          <DrawerBody>
            <p>This drawer uses the flat alias exports.</p>
          </DrawerBody>
          <DrawerFooter>
            <ActionButton secondary onPress={() => setIsOpen(false)}>
              Close
            </ActionButton>
          </DrawerFooter>
        </DrawerContent>
      </DrawerPrimitive>
    </>
  );
};

// Placement is exercised interactively so reviewers can confirm the drawer
// slides in from every supported edge without four near-duplicate stories.
export const Placement: Story = () => {
  const [isOpen, setIsOpen] = useState(true);
  const [placement, setPlacement] = useState<Placement>('right');

  const placements: Placement[] = ['left', 'right', 'top', 'bottom'];

  return (
    <div className="flex flex-col gap-3 p-6">
      <div className="flex flex-wrap gap-2">
        {placements.map((side) => (
          <ActionButton
            key={side}
            primary
            onPress={() => {
              setPlacement(side);
              setIsOpen(true);
            }}
          >
            Open {side}
          </ActionButton>
        ))}
      </div>
      <DrawerPrimitive
        isOpen={isOpen}
        placement={placement}
        onOpenChange={() => setIsOpen(false)}
      >
        <DrawerContent>
          <DrawerHeader>Placement: {placement}</DrawerHeader>
          <DrawerBody>
            <p>The drawer enters from the {placement} edge.</p>
          </DrawerBody>
          <DrawerFooter>
            <ActionButton secondary onPress={() => setIsOpen(false)}>
              Close
            </ActionButton>
          </DrawerFooter>
        </DrawerContent>
      </DrawerPrimitive>
    </div>
  );
};

export const Sizes: Story = () => {
  const [isOpen, setIsOpen] = useState(true);
  const [size, setSize] = useState<Size>('md');

  const sizes: Size[] = ['sm', 'md', 'lg', 'xl', 'full'];

  return (
    <div className="flex flex-col gap-3 p-6">
      <div className="flex flex-wrap gap-2">
        {sizes.map((value) => (
          <ActionButton
            key={value}
            primary
            onPress={() => {
              setSize(value);
              setIsOpen(true);
            }}
          >
            Open {value}
          </ActionButton>
        ))}
      </div>
      <DrawerPrimitive
        isOpen={isOpen}
        size={size}
        onOpenChange={() => setIsOpen(false)}
      >
        <DrawerContent>
          <DrawerHeader>Size: {size}</DrawerHeader>
          <DrawerBody>
            <p>The drawer width follows the selected size token.</p>
          </DrawerBody>
          <DrawerFooter>
            <ActionButton secondary onPress={() => setIsOpen(false)}>
              Close
            </ActionButton>
          </DrawerFooter>
        </DrawerContent>
      </DrawerPrimitive>
    </div>
  );
};
