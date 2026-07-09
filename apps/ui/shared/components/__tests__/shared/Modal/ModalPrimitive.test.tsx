// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import {
  ModalPrimitive,
  ModalPrimitiveBody,
  ModalPrimitiveContent,
  ModalPrimitiveFooter,
  ModalPrimitiveHeader,
} from '@/src/Modal/ModalPrimitive';

describe('ModalPrimitive', () => {
  it('re-exports HeroUI Modal as ModalPrimitive', () => {
    expect(ModalPrimitive).toBeDefined();
  });

  it('exposes compound sub-components', () => {
    expect(ModalPrimitive.Body).toBe(ModalPrimitiveBody);
    expect(ModalPrimitive.Content).toBe(ModalPrimitiveContent);
    expect(ModalPrimitive.Footer).toBe(ModalPrimitiveFooter);
    expect(ModalPrimitive.Header).toBe(ModalPrimitiveHeader);
  });

  it('renders an open modal with all sections', async () => {
    await act(() => {
      render(
        <ModalPrimitive isOpen onOpenChange={() => {}}>
          <ModalPrimitive.Content>
            <ModalPrimitive.Header>Test Title</ModalPrimitive.Header>
            <ModalPrimitive.Body>Test Body</ModalPrimitive.Body>
            <ModalPrimitive.Footer>Test Footer</ModalPrimitive.Footer>
          </ModalPrimitive.Content>
        </ModalPrimitive>,
      );
    });

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Body')).toBeInTheDocument();
    expect(screen.getByText('Test Footer')).toBeInTheDocument();
  });

  it('does not render content when closed', () => {
    render(
      <ModalPrimitive isOpen={false} onOpenChange={() => {}}>
        <ModalPrimitive.Content>
          <ModalPrimitive.Header>Hidden Title</ModalPrimitive.Header>
          <ModalPrimitive.Body>Hidden Body</ModalPrimitive.Body>
        </ModalPrimitive.Content>
      </ModalPrimitive>,
    );

    expect(screen.queryByText('Hidden Title')).not.toBeInTheDocument();
    expect(screen.queryByText('Hidden Body')).not.toBeInTheDocument();
  });

  it('calls onOpenChange when close button is clicked', async () => {
    const onOpenChange = vi.fn();

    await act(() => {
      render(
        <ModalPrimitive isOpen onOpenChange={onOpenChange}>
          <ModalPrimitive.Content>
            <ModalPrimitive.Header>Closable</ModalPrimitive.Header>
            <ModalPrimitive.Body>Content</ModalPrimitive.Body>
          </ModalPrimitive.Content>
        </ModalPrimitive>,
      );
    });

    const closeButton = screen.getByRole('button', { name: /close/i });
    await act(() => {
      fireEvent.click(closeButton);
    });

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('renders using flat alias imports', async () => {
    await act(() => {
      render(
        <ModalPrimitive isOpen onOpenChange={() => {}}>
          <ModalPrimitiveContent>
            <ModalPrimitiveHeader>Flat Header</ModalPrimitiveHeader>
            <ModalPrimitiveBody>Flat Body</ModalPrimitiveBody>
            <ModalPrimitiveFooter>Flat Footer</ModalPrimitiveFooter>
          </ModalPrimitiveContent>
        </ModalPrimitive>,
      );
    });

    expect(screen.getByText('Flat Header')).toBeInTheDocument();
    expect(screen.getByText('Flat Body')).toBeInTheDocument();
    expect(screen.getByText('Flat Footer')).toBeInTheDocument();
  });
});
