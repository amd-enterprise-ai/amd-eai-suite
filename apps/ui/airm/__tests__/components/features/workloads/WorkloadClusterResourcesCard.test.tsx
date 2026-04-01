// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { WorkloadClusterResourcesCard } from '@/components/features/workloads/WorkloadClusterResourcesCard';

import wrapper from '@/__tests__/ProviderWrapper';

describe('WorkloadClusterResourcesCard', () => {
  it('should render the section title', () => {
    render(<WorkloadClusterResourcesCard />, { wrapper });
    expect(
      screen.getByText('details.sections.clusterAndResources'),
    ).toBeInTheDocument();
  });

  it('should render all field labels', () => {
    render(<WorkloadClusterResourcesCard />, { wrapper });
    expect(screen.getByText('details.fields.cluster')).toBeInTheDocument();
    expect(screen.getByText('details.fields.id')).toBeInTheDocument();
    expect(screen.getByText('details.fields.nodesInUse')).toBeInTheDocument();
    expect(
      screen.getByText('details.fields.gpuDevicesInUse'),
    ).toBeInTheDocument();
  });

  it('should render data values when loaded', () => {
    render(
      <WorkloadClusterResourcesCard
        clusterName="demo-cluster"
        clusterId="cluster-1"
        nodesInUse={2}
        gpuDevicesInUse={4}
        isLoading={false}
      />,
      { wrapper },
    );
    expect(screen.getByText('demo-cluster')).toBeInTheDocument();
    expect(screen.getByText('cluster-1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('should render em dashes for missing cluster name', () => {
    render(
      <WorkloadClusterResourcesCard
        clusterName={null}
        clusterId={null}
        nodesInUse={0}
        gpuDevicesInUse={0}
        isLoading={false}
      />,
      { wrapper },
    );
    const dashes = screen.getAllByText('—');
    expect(dashes).toHaveLength(2);
  });

  it('should render placeholder dashes when loading', () => {
    render(<WorkloadClusterResourcesCard isLoading />, { wrapper });
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(3);
  });

  it('should not render data values when loading', () => {
    render(
      <WorkloadClusterResourcesCard
        clusterName="demo-cluster"
        clusterId="cluster-1"
        nodesInUse={2}
        gpuDevicesInUse={4}
        isLoading
      />,
      { wrapper },
    );
    expect(screen.queryByText('demo-cluster')).not.toBeInTheDocument();
    expect(screen.queryByText('cluster-1')).not.toBeInTheDocument();
  });
});
