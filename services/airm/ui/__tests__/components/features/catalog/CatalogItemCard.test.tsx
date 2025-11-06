// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import { CatalogItem } from '@/types/catalog';
import { CatalogItemCategory, CatalogItemType } from '@/types/enums/catalog';

import { CatalogItemCard } from '@/components/features/catalog/CatalogItemCard';

describe('CatalogItemCard', () => {
  const mockItem: CatalogItem = {
    id: 'item-1',
    name: 'Test Catalog Item',
    displayName: 'Test Catalog Item',
    slug: 'test-catalog-item',
    description: 'Short description',
    longDescription: 'Long description',
    type: CatalogItemType.WORKSPACE,
    category: CatalogItemCategory.DEVELOPMENT,
    createdAt: '2023-01-01T00:00:00Z',
    tags: ['tag1', 'tag2'],
    featuredImage: '',
    requiredResources: {
      gpuCount: 1,
      gpuMemory: 8,
      cpuCoreCount: 4,
      systemMemory: 16,
    },
    available: true,
    externalUrl: 'https://example.com',
    workloadsCount: 0,
    workloads: [],
  };

  const primaryAction = {
    key: 'view',
    label: 'View',
    onPress: vi.fn(),
  };
  const secondaryAction = {
    key: 'secondary',
    label: 'Secondary',
    onPress: vi.fn(),
  };

  const readyAction = {
    key: 'ready',
    label: 'Launch',
    onPress: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the card with name, description, and tags', () => {
    render(
      <CatalogItemCard
        item={mockItem}
        primaryAction={primaryAction}
        secondaryAction={secondaryAction}
        pendingLabel={'Pending'}
        readyAction={readyAction}
      />,
    );
    expect(screen.getByText('Test Catalog Item')).toBeInTheDocument();
    expect(screen.getByText('Short description')).toBeInTheDocument();
    expect(screen.getByText('tag1')).toBeInTheDocument();
    expect(screen.getByText('tag2')).toBeInTheDocument();
    expect(screen.getByText('View')).toBeInTheDocument();
    expect(screen.getByText('Secondary')).toBeInTheDocument();
  });

  it('calls primaryActionClick when card header or primary button is clicked', () => {
    render(
      <CatalogItemCard
        item={mockItem}
        primaryAction={primaryAction}
        pendingLabel={'Pending'}
        readyAction={readyAction}
      />,
    );

    // Click on primary action button
    fireEvent.click(screen.getByText('View'));
    expect(primaryAction.onPress).toHaveBeenCalledTimes(1);
  });

  it('calls secondaryActionClick when secondary button is clicked', () => {
    render(
      <CatalogItemCard
        item={mockItem}
        primaryAction={primaryAction}
        secondaryAction={secondaryAction}
        pendingLabel={'Pending'}
        readyAction={readyAction}
      />,
    );
    fireEvent.click(screen.getByText('Secondary'));
    expect(secondaryAction.onPress).toHaveBeenCalledWith(mockItem);
  });

  it('opens external link when external link button is clicked', () => {
    window.open = vi.fn();
    render(
      <CatalogItemCard
        item={mockItem}
        primaryAction={primaryAction}
        pendingLabel={'Pending'}
        readyAction={readyAction}
      />,
    );
    const externalButton = screen.getByRole('button', { name: '' });
    fireEvent.click(externalButton);
    expect(window.open).toHaveBeenCalledWith('https://example.com', '_blank');
  });

  it('disables actions and buttons when item is not available', () => {
    render(
      <CatalogItemCard
        item={{ ...mockItem, available: false }}
        primaryAction={primaryAction}
        secondaryAction={secondaryAction}
        pendingLabel={'Pending'}
        readyAction={readyAction}
      />,
    );
    expect(screen.getByText('View')).toBeDisabled();
    expect(screen.getByText('Secondary')).toBeDisabled();
  });

  it('disables external link button if no externalUrl', () => {
    render(
      <CatalogItemCard
        item={{ ...mockItem, externalUrl: '' }}
        primaryAction={primaryAction}
        pendingLabel={'Pending'}
        readyAction={readyAction}
      />,
    );
    const externalButton = screen.getByRole('button', { name: '' });
    expect(externalButton).toBeDisabled();
  });
});
