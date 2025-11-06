// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { generateClustersMock } from '../../../../__mocks__/utils/cluster-mock';

import { ClusterStatus } from '@/types/enums/cluster-status';
import { QuotaResource } from '@/types/enums/quotas';
import { WorkloadsStats } from '@/types/workloads';

import { ClusterStats } from '@/components/features/clusters';

describe('ClusterStats', () => {
  it('should render the component', async () => {
    const mockCluster = generateClustersMock(1)[0];

    const mockWorkloadsStats: WorkloadsStats = {
      runningWorkloadsCount: 10,
    };

    await act(() => {
      render(
        <ClusterStats
          cluster={mockCluster}
          workloadsStats={mockWorkloadsStats}
        />,
      );
    });
    const header = screen.getByText('statistics.cluster.nodes.title');
    expect(header).toBeInTheDocument();

    const workloadsHeader = screen.getByText(
      'statistics.cluster.workloads.title',
    );
    expect(workloadsHeader).toBeInTheDocument();
    const workloadsParent =
      workloadsHeader.parentElement?.parentElement?.parentElement;
    expect(workloadsParent).toHaveTextContent(
      'statistics.cluster.workloads.title10',
    );
  });
});
