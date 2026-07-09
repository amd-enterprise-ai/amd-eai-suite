// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import {
  DrawerPrimitive,
  DrawerBody,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
} from '@amdenterpriseai/components';

import '@testing-library/jest-dom';

describe('DrawerPrimitive adapter', () => {
  it('exposes compound sub-components', () => {
    expect(DrawerPrimitive.Body).toBe(DrawerBody);
    expect(DrawerPrimitive.Content).toBe(DrawerContent);
    expect(DrawerPrimitive.Footer).toBe(DrawerFooter);
    expect(DrawerPrimitive.Header).toBe(DrawerHeader);
  });

  it('renders with compound component API', () => {
    render(
      <DrawerPrimitive isOpen onOpenChange={() => {}}>
        <DrawerPrimitive.Content>
          <DrawerPrimitive.Header>Test Title</DrawerPrimitive.Header>
          <DrawerPrimitive.Body>Test Body</DrawerPrimitive.Body>
          <DrawerPrimitive.Footer>Test Footer</DrawerPrimitive.Footer>
        </DrawerPrimitive.Content>
      </DrawerPrimitive>,
    );

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Body')).toBeInTheDocument();
    expect(screen.getByText('Test Footer')).toBeInTheDocument();
  });

  it('renders with flat alias API', () => {
    render(
      <DrawerPrimitive isOpen onOpenChange={() => {}}>
        <DrawerContent>
          <DrawerHeader>Flat Title</DrawerHeader>
          <DrawerBody>Flat Body</DrawerBody>
          <DrawerFooter>Flat Footer</DrawerFooter>
        </DrawerContent>
      </DrawerPrimitive>,
    );

    expect(screen.getByText('Flat Title')).toBeInTheDocument();
    expect(screen.getByText('Flat Body')).toBeInTheDocument();
    expect(screen.getByText('Flat Footer')).toBeInTheDocument();
  });
});
