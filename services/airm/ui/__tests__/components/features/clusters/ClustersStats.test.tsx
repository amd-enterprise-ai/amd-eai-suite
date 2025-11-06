// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { generateClustersMock } from '../../../../__mocks__/utils/cluster-mock';

import { WorkloadsStats } from '@/types/workloads';

import { ClustersStats } from '@/components/features/clusters';

describe('ClustersStats', () => {
  it('should render the component', () => {
    const mockClusters = generateClustersMock(2);

    const mockWorkloadsStats: WorkloadsStats = {
      runningWorkloadsCount: 13,
    };

    act(() => {
      render(
        <ClustersStats
          clusters={mockClusters}
          workloadsStats={mockWorkloadsStats}
        />,
      );
    });
    const clustersHeader = screen.getByText(
      'statistics.clusters.clusters.title',
    );
    expect(clustersHeader).toBeInTheDocument();
    const clustersParent =
      clustersHeader.parentElement?.parentElement?.parentElement;
    expect(clustersParent).toHaveTextContent(
      'statistics.clusters.clusters.title2',
    );

    const nodesHeader = screen.getByText('statistics.clusters.nodes.title');
    expect(nodesHeader).toBeInTheDocument();
    const nodesParent = nodesHeader.parentElement?.parentElement?.parentElement;
    expect(nodesParent).toHaveTextContent(
      'statistics.clusters.nodes.title7statistics.upperLimitPrefix 13',
    );

    const gpusHeader = screen.getByText('statistics.clusters.gpus.title');
    expect(gpusHeader).toBeInTheDocument();
    const gpusParent = gpusHeader.parentElement?.parentElement?.parentElement;
    expect(gpusParent).toHaveTextContent(
      'statistics.clusters.gpus.title4statistics.upperLimitPrefix 8',
    );

    const workloadsHeader = screen.getByText(
      'statistics.clusters.workloads.title',
    );
    expect(workloadsHeader).toBeInTheDocument();
    const workloadsParent =
      workloadsHeader.parentElement?.parentElement?.parentElement;
    expect(workloadsParent).toHaveTextContent(
      'statistics.clusters.workloads.title13',
    );
  });
});
