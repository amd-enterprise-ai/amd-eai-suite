// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { WorkloadStatus } from '@/types/enums/workloads';

import { ProjectWorkloadsStatsCard } from '@/components/features/projects';

describe('ProjectWorkloadsStatsCard', () => {
  it('renders component with correct project name', () => {
    const { container } = render(
      <ProjectWorkloadsStatsCard
        projectName={'test-project'}
        totalWorkloads={10}
        data={[]}
      />,
    );
    expect(container).toBeTruthy();
    expect(
      screen.getByText('dashboard.overview.workloadStates.title'),
    ).toBeInTheDocument();
    expect(screen.getByText('test-project')).toBeInTheDocument();
  });

  it('renders component with correct workloads total', () => {
    act(() => {
      render(
        <ProjectWorkloadsStatsCard
          projectName={'test-project'}
          totalWorkloads={10}
          data={[]}
        />,
      );
    });

    expect(
      screen.getByText('dashboard.overview.workloadStates.total'),
    ).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders component correct with data', () => {
    act(() => {
      render(
        <ProjectWorkloadsStatsCard
          projectName={'test-project'}
          totalWorkloads={10}
          data={[
            {
              status: WorkloadStatus.RUNNING,
              count: 5,
            },
            {
              status: WorkloadStatus.PENDING,
              count: 3,
            },
          ]}
        />,
      );
    });

    expect(
      screen.getByText('dashboard.overview.workloadStates.subtitle'),
    ).toBeInTheDocument();
    expect(screen.getByText('status.Running')).toBeInTheDocument();
    expect(screen.getByText('status.Pending')).toBeInTheDocument();
    const ratioElements = screen.getAllByText('(', { exact: false });
    expect(ratioElements[0].parentElement).toHaveTextContent('(5/10)');
    expect(ratioElements[1].parentElement).toHaveTextContent('(3/10)');
  });

  it('renders component in loading state will not render some key info', () => {
    act(() => {
      render(
        <ProjectWorkloadsStatsCard
          projectName={'test-project'}
          totalWorkloads={0}
          data={[]}
          isLoading
        />,
      );
    });

    expect(
      screen.queryByText('dashboard.overview.workloadStates.total'),
    ).not.toBeInTheDocument();
    expect(screen.queryByText('10')).not.toBeInTheDocument();
  });
});
