// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent } from '@testing-library/react';

import {
  DatasetDownloadIndicator,
  DownloadStatus,
} from '@/components/features/datasets/DatasetDownloadIndicator';

import wrapper from '@/__tests__/ProviderWrapper';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('DatasetDownloadIndicator', () => {
  const mockOnDismiss = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders preparing state with correct text', () => {
    render(
      <DatasetDownloadIndicator
        status={DownloadStatus.PREPARING}
        onDismiss={mockOnDismiss}
      />,
      { wrapper },
    );

    expect(
      screen.getByText('download.indicator.preparing.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('download.indicator.preparing.subtitle'),
    ).toBeInTheDocument();
  });

  it('renders done state with correct text', () => {
    render(
      <DatasetDownloadIndicator
        status={DownloadStatus.DONE}
        onDismiss={mockOnDismiss}
      />,
      { wrapper },
    );

    expect(
      screen.getByText('download.indicator.done.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('download.indicator.done.subtitle'),
    ).toBeInTheDocument();
  });

  it('calls onDismiss when the dismiss button is clicked', () => {
    render(
      <DatasetDownloadIndicator
        status={DownloadStatus.PREPARING}
        onDismiss={mockOnDismiss}
      />,
      { wrapper },
    );

    fireEvent.click(screen.getByLabelText('download.indicator.dismiss'));

    expect(mockOnDismiss).toHaveBeenCalledOnce();
  });
});
