// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { GPUMemoryUsageCard } from '@/components/features/projects';

// Mock useTranslation from next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (key === 'dashboard.overview.vramDeviceUsage.upperLimit')
        return `Limit: ${opts?.num}`;
      return key;
    },
  }),
}));

const mockData = {
  numerator: [
    { timestamp: '2024-06-10T12:00:00.000Z', value: 10240 },
    { timestamp: '2024-06-10T12:10:00.000Z', value: 20480 },
    { timestamp: '2024-06-10T12:20:00.000Z', value: 30720 },
  ],
  denominator: [
    { timestamp: '2024-06-10T12:00:00.000Z', value: 40960 },
    { timestamp: '2024-06-10T12:10:00.000Z', value: 51200 },
    { timestamp: '2024-06-10T12:20:00.000Z', value: 61440 },
  ],
};

describe('GPUMemoryUsageCard', () => {
  it('renders with correct props and translations', () => {
    act(() => {
      render(<GPUMemoryUsageCard data={mockData} />);
    });
    expect(
      screen.getByText('dashboard.overview.vramDeviceUsage.title'),
    ).toBeInTheDocument();
    expect(screen.getByText('30.00 GB')).toBeInTheDocument();
    expect(screen.getByText('Limit: 60.00 GB')).toBeInTheDocument();
  });

  it('shows loading state when isLoading is true', () => {
    act(() => {
      render(<GPUMemoryUsageCard data={mockData} isLoading />);
    });
    expect(screen.queryByText('30.00 GB')).not.toBeInTheDocument();
  });
});
