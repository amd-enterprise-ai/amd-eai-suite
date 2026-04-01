// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { act, render, screen } from '@testing-library/react';

import { generateMockStorages } from '@/__mocks__/utils/storages-mock';

import { StoragesTable } from '@/components/features/storages';

import wrapper from '@/__tests__/ProviderWrapper';

describe('StoragesTable', () => {
  const storages = generateMockStorages(1)[0];

  const setup = (
    props?: Partial<React.ComponentProps<typeof StoragesTable>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <StoragesTable storages={[]} isStoragesLoading={false} {...props} />,
        { wrapper },
      );
    });
    return { onOpenChange };
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('render without projectId', () => {
    setup();
    expect(screen.getByText('list.headers.name.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.type.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.status.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.scope.title')).toBeInTheDocument();
    expect(
      screen.getByText('list.headers.assignedTo.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('list.headers.createdAt.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('list.headers.createdBy.title'),
    ).toBeInTheDocument();
  });
});
