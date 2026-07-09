// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { LoadingState } from '@/components/shared/PageErrorHandler/LoadingState';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('@/components/shared/PageLoader', () => ({
  PageLoader: ({
    label,
    className,
  }: {
    label?: string;
    className?: string;
  }) => (
    <div data-testid="page-loader" data-classname={className}>
      {label && <span>{label}</span>}
    </div>
  ),
}));

describe('LoadingState', () => {
  it('renders PageLoader with the loading label', () => {
    render(<LoadingState />);

    expect(screen.getByTestId('page-loader')).toBeInTheDocument();
    expect(screen.getByText('pageLoader.loading')).toBeInTheDocument();
  });

  it('passes full-height className to PageLoader', () => {
    render(<LoadingState />);

    expect(screen.getByTestId('page-loader')).toHaveAttribute(
      'data-classname',
      'w-full h-full',
    );
  });
});
