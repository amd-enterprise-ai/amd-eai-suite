// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { WorkloadStatus } from '@amdenterpriseai/types';

import { ClusterWorkloadsStatsCard } from '@/components/features/clusters';

import wrapper from '@/__tests__/ProviderWrapper';

const mockData = [
  { status: WorkloadStatus.RUNNING, count: 5 },
  { status: WorkloadStatus.PENDING, count: 3 },
  { status: WorkloadStatus.COMPLETE, count: 10 },
  { status: WorkloadStatus.FAILED, count: 2 },
];

describe('ClusterWorkloadsStatsCard', () => {
  it('renders component with data', () => {
    const { container } = render(
      <ClusterWorkloadsStatsCard
        clusterName="Test Cluster"
        totalWorkloads={20}
        data={mockData}
        isLoading={false}
      />,
      { wrapper },
    );
    expect(container).toBeTruthy();
  });

  it('renders cluster name', () => {
    render(
      <ClusterWorkloadsStatsCard
        clusterName="Test Cluster"
        totalWorkloads={20}
        data={mockData}
        isLoading={false}
      />,
      { wrapper },
    );
    expect(screen.getByText('Test Cluster')).toBeInTheDocument();
  });

  it('renders total workloads count', () => {
    render(
      <ClusterWorkloadsStatsCard
        clusterName="Test Cluster"
        totalWorkloads={20}
        data={mockData}
        isLoading={false}
      />,
      { wrapper },
    );
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('renders loading state', () => {
    const { container } = render(
      <ClusterWorkloadsStatsCard
        clusterName="Test Cluster"
        totalWorkloads={20}
        data={mockData}
        isLoading={true}
      />,
      { wrapper },
    );
    expect(container).toBeTruthy();
  });

  it('renders with empty data', () => {
    const { container } = render(
      <ClusterWorkloadsStatsCard
        clusterName="Test Cluster"
        totalWorkloads={0}
        data={[]}
        isLoading={false}
      />,
      { wrapper },
    );
    expect(container).toBeTruthy();
    expect(screen.getByText('Test Cluster')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});
