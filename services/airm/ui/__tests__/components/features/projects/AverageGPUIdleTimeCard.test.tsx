// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { AverageGPUIdleTimeCard } from '@/components/features/projects';

const mockData = (data: number) => ({
  data,
  range: {
    start: `2024-01-01T00:00:01Z`,
    end: `2024-01-01T00:00:02Z`,
  },
});

describe('GPUIdleTimeCard', () => {
  it('renders loading state', () => {
    act(() => {
      render(<AverageGPUIdleTimeCard data={mockData(1)} isLoading={true} />);
    });
    expect(
      screen.getByText('dashboard.overview.gpuIdleTimeAvg.title'),
    ).toBeInTheDocument();
  });

  it('renders 0 data value is undefined empty', () => {
    act(() => {
      render(<AverageGPUIdleTimeCard data={undefined} />);
    });
    expect(screen.getByText('0s')).toBeInTheDocument();
  });

  it('calculates and renders correct time correctly', () => {
    act(() => {
      render(<AverageGPUIdleTimeCard data={mockData(60)} />);
    });
    expect(screen.getByText('1m')).toBeInTheDocument();
  });

  it('calculates and renders correct time correctly for hours', () => {
    act(() => {
      render(<AverageGPUIdleTimeCard data={mockData(3600)} />);
    });
    expect(screen.getByText('1h')).toBeInTheDocument();
  });
});
