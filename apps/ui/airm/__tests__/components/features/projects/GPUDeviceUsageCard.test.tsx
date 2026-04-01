// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { GPUDeviceUsageCard } from '@/components/features/projects';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (key === 'dashboard.overview.gpuDeviceUsage.upperLimit' && opts) {
        return `Upper Limit: ${opts.num}`;
      }
      return key;
    },
  }),
}));

const mockData = {
  numerator: [
    { timestamp: '1', value: 1 },
    { timestamp: '2', value: 2 },
    { timestamp: '3', value: 3 },
  ],
  denominator: [
    { timestamp: '1', value: 4 },
    { timestamp: '2', value: 5 },
    { timestamp: '3', value: 6 },
  ],
};

describe('GPUDeviceUsageCard', () => {
  it('renders with required props', () => {
    act(() => {
      render(<GPUDeviceUsageCard data={mockData} />);
    });
    expect(
      screen.getByText('dashboard.overview.gpuDeviceUsage.title'),
    ).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Upper Limit: 6')).toBeInTheDocument();
  });

  it('passes isLoading prop', () => {
    act(() => {
      render(<GPUDeviceUsageCard data={mockData} isLoading />);
    });
    expect(screen.queryByText('3')).not.toBeInTheDocument();
    expect(screen.queryByText('Upper Limit: 6')).not.toBeInTheDocument();
  });
});
