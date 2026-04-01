// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { WorkloadTimelineCard } from '@/components/features/workloads/WorkloadTimelineCard';

import wrapper from '@/__tests__/ProviderWrapper';

vi.mock('@amdenterpriseai/utils/app', async (importOriginal) => ({
  ...(await importOriginal()),
  displayTimestamp: (date: Date) => `formatted:${date.toISOString()}`,
  formatDurationFromSeconds: (seconds: number) => `${seconds}s`,
}));

describe('WorkloadTimelineCard', () => {
  const defaultProps = {
    createdAt: '2025-10-07T19:48:00Z',
    updatedAt: '2025-10-07T19:53:00Z',
  };

  it('should render the section title', () => {
    render(<WorkloadTimelineCard {...defaultProps} />, { wrapper });
    expect(screen.getByText('details.sections.timeline')).toBeInTheDocument();
  });

  it('should render all field labels', () => {
    render(<WorkloadTimelineCard {...defaultProps} />, { wrapper });
    expect(screen.getByText('details.fields.createdAt')).toBeInTheDocument();
    expect(screen.getByText('details.fields.updatedAt')).toBeInTheDocument();
    expect(screen.getByText('details.fields.queueTime')).toBeInTheDocument();
    expect(screen.getByText('details.fields.runningTime')).toBeInTheDocument();
  });

  it('should render formatted timestamps', () => {
    render(<WorkloadTimelineCard {...defaultProps} />, { wrapper });
    expect(
      screen.getByText('formatted:2025-10-07T19:48:00.000Z'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('formatted:2025-10-07T19:53:00.000Z'),
    ).toBeInTheDocument();
  });

  it('should render em dashes when queue and running time are absent', () => {
    render(<WorkloadTimelineCard {...defaultProps} />, { wrapper });
    const dashes = screen.getAllByText('—');
    expect(dashes).toHaveLength(2);
  });

  it('should render formatted durations when provided', () => {
    render(
      <WorkloadTimelineCard
        {...defaultProps}
        queueTime={120}
        runningTime={3600}
      />,
      { wrapper },
    );
    expect(screen.getByText('120s')).toBeInTheDocument();
    expect(screen.getByText('3600s')).toBeInTheDocument();
  });
});
