// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen, waitFor } from '@testing-library/react';
import { format } from 'date-fns';

import { fetchNodeWorkloadsMetrics } from '@/services/app';
import { getClusterProjects } from '@/services/app';

import { NodeWorkloadsTable } from '@/components/features/clusters';

import wrapper from '@/__tests__/ProviderWrapper';
import {
  generateNodeWorkloadsMock,
  generateClusterProjectsMock,
} from '@/__mocks__/utils/cluster-mock';

const mockNodeWorkloads = generateNodeWorkloadsMock(2, 'worker-1');
const mockClusterProjects = generateClusterProjectsMock(2);

vi.mock('@/services/app', () => ({
  fetchNodeWorkloadsMetrics: vi.fn(() =>
    Promise.resolve({
      data: mockNodeWorkloads,
    }),
  ),
  getClusterProjects: vi.fn(() =>
    Promise.resolve({
      data: mockClusterProjects,
    }),
  ),
}));

describe('NodeWorkloadsTable', () => {
  it('renders component and calls fetchNodeWorkloadsMetrics', () => {
    const { container } = render(
      <NodeWorkloadsTable
        clusterId="cluster-1"
        nodeId="node-1"
        nodeName="worker-1"
      />,
      { wrapper },
    );
    expect(container).toBeTruthy();
    expect(fetchNodeWorkloadsMetrics).toHaveBeenCalledWith(
      'cluster-1',
      'node-1',
    );
    expect(getClusterProjects).toHaveBeenCalledWith('cluster-1');
  });

  it('renders workload names', async () => {
    await act(() => {
      render(
        <NodeWorkloadsTable
          clusterId="cluster-1"
          nodeId="node-1"
          nodeName="worker-1"
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(mockNodeWorkloads[0].displayName!),
      ).toBeInTheDocument();
      expect(
        screen.getByText(mockNodeWorkloads[1].displayName!),
      ).toBeInTheDocument();
    });
  });

  it('renders correct status', async () => {
    await act(() => {
      render(
        <NodeWorkloadsTable
          clusterId="cluster-1"
          nodeId="node-1"
          nodeName="worker-1"
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText('list.nodes.detail.workloads.headers.status.title'),
      ).toBeInTheDocument();
      expect(
        screen.getByText(`status.${mockNodeWorkloads[0].status}`),
      ).toBeInTheDocument();
      expect(
        screen.getByText(`status.${mockNodeWorkloads[1].status}`),
      ).toBeInTheDocument();
    });
  });

  it('renders correct VRAM', async () => {
    await act(() => {
      render(
        <NodeWorkloadsTable
          clusterId="cluster-1"
          nodeId="node-1"
          nodeName="worker-1"
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText('list.nodes.detail.workloads.headers.vram.title'),
      ).toBeInTheDocument();
      expect(screen.getByText('8 GB')).toBeInTheDocument();
      expect(screen.getByText('16 GB')).toBeInTheDocument();
    });
  });

  it('renders correct created time', async () => {
    await act(() => {
      render(
        <NodeWorkloadsTable
          clusterId="cluster-1"
          nodeId="node-1"
          nodeName="worker-1"
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          format(new Date(mockNodeWorkloads[0].createdAt), 'yyyy/MM/dd HH:mm'),
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          format(new Date(mockNodeWorkloads[1].createdAt), 'yyyy/MM/dd HH:mm'),
        ),
      ).toBeInTheDocument();
    });
  });

  it('renders project names', async () => {
    await act(() => {
      render(
        <NodeWorkloadsTable
          clusterId="cluster-1"
          nodeId="node-1"
          nodeName="worker-1"
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(screen.getByText(mockClusterProjects[0].name)).toBeInTheDocument();
      expect(screen.getByText(mockClusterProjects[1].name)).toBeInTheDocument();
    });
  });

  it('renders GPU devices count for multi-device workload', async () => {
    await act(() => {
      render(
        <NodeWorkloadsTable
          clusterId="cluster-1"
          nodeId="node-1"
          nodeName="worker-1"
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText('nodes.detail.workloads.gpuDevices.devices'),
      ).toBeInTheDocument();
    });
  });

  it('renders single GPU device name for single-device workload', async () => {
    await act(() => {
      render(
        <NodeWorkloadsTable
          clusterId="cluster-1"
          nodeId="node-1"
          nodeName="worker-1"
        />,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(screen.getByText('gpu-1')).toBeInTheDocument();
    });
  });
});
