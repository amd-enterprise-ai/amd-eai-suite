// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ClusterNode } from '@amdenterpriseai/types';
import { WorkloadGpuDeviceSnapshot } from '@/types/workloads';

import { GpuDeviceMetricsGrid } from '@/components/features/workloads/GpuDeviceMetricsGrid';

import wrapper from '@/__tests__/ProviderWrapper';

const mockPush = vi.fn();

vi.mock('next/router', () => ({
  useRouter: () => ({
    push: mockPush,
    query: {},
  }),
}));

vi.mock('@amdenterpriseai/components', () => ({
  StatsWithLineChart: ({ title }: { title: string }) => (
    <div data-testid="stats-chart">{title}</div>
  ),
}));

const makeDevice = (
  overrides: Partial<WorkloadGpuDeviceSnapshot> = {},
): WorkloadGpuDeviceSnapshot => ({
  gpuUuid: 'gpu-uuid-0',
  gpuId: '0',
  hostname: 'node-host-1',
  vramUtilizationPct: 50,
  junctionTemperatureC: 60,
  powerUsageW: 200,
  vramUtilizationSeries: [{ time: '2025-01-01T00:00:00Z', value: 50 }],
  junctionTemperatureSeries: [{ time: '2025-01-01T00:00:00Z', value: 60 }],
  powerUsageSeries: [{ time: '2025-01-01T00:00:00Z', value: 200 }],
  ...overrides,
});

const makeNode = (overrides: Partial<ClusterNode> = {}): ClusterNode =>
  ({
    id: 'node-id-1',
    name: 'node-host-1',
    ...overrides,
  }) as ClusterNode;

describe('GpuDeviceMetricsGrid', () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it('should render device name and hostname', () => {
    const device = makeDevice();
    render(
      <GpuDeviceMetricsGrid
        devices={[device]}
        nodesByHostname={new Map()}
        isFetching={false}
      />,
      { wrapper },
    );
    expect(screen.getByText('gpu-device-0')).toBeInTheDocument();
    expect(
      screen.getByText('(node-host-1)', { exact: false }),
    ).toBeInTheDocument();
  });

  it('should use displayLabel when available', () => {
    const device = makeDevice({ displayLabel: 'MI300X #0' });
    render(
      <GpuDeviceMetricsGrid
        devices={[device]}
        nodesByHostname={new Map()}
        isFetching={false}
      />,
      { wrapper },
    );
    expect(screen.getByText('MI300X #0')).toBeInTheDocument();
  });

  it('should not render hostname span when hostname is absent', () => {
    const device = makeDevice({ hostname: '' });
    render(
      <GpuDeviceMetricsGrid
        devices={[device]}
        nodesByHostname={new Map()}
        isFetching={false}
      />,
      { wrapper },
    );
    expect(screen.getByText('gpu-device-0')).toBeInTheDocument();
    expect(screen.queryByText(/\(/)).not.toBeInTheDocument();
  });

  it('should render three metric charts per device', () => {
    const device = makeDevice();
    render(
      <GpuDeviceMetricsGrid
        devices={[device]}
        nodesByHostname={new Map()}
        isFetching={false}
      />,
      { wrapper },
    );
    expect(screen.getAllByTestId('stats-chart')).toHaveLength(3);
    expect(
      screen.getByText('details.fields.memoryUtilization'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('details.fields.junctionTemperature'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('details.fields.gpuPowerUsage'),
    ).toBeInTheDocument();
  });

  it('should show View all metrics button when node matches', () => {
    const device = makeDevice();
    const node = makeNode();
    const nodesByHostname = new Map([['node-host-1', node]]);

    render(
      <GpuDeviceMetricsGrid
        devices={[device]}
        nodesByHostname={nodesByHostname}
        clusterId="cluster-1"
        isFetching={false}
      />,
      { wrapper },
    );
    expect(
      screen.getByRole('button', { name: 'details.fields.viewAllMetrics' }),
    ).toBeInTheDocument();
  });

  it('should not show View all metrics button when no node matches', () => {
    const device = makeDevice({ hostname: 'unknown-host' });
    render(
      <GpuDeviceMetricsGrid
        devices={[device]}
        nodesByHostname={new Map()}
        isFetching={false}
      />,
      { wrapper },
    );
    expect(
      screen.queryByRole('button', { name: 'details.fields.viewAllMetrics' }),
    ).not.toBeInTheDocument();
  });

  it('should navigate to correct node page on button click', async () => {
    const user = userEvent.setup();
    const device = makeDevice();
    const node = makeNode();
    const nodesByHostname = new Map([['node-host-1', node]]);

    render(
      <GpuDeviceMetricsGrid
        devices={[device]}
        nodesByHostname={nodesByHostname}
        clusterId="cluster-1"
        isFetching={false}
      />,
      { wrapper },
    );

    await user.click(
      screen.getByRole('button', { name: 'details.fields.viewAllMetrics' }),
    );
    expect(mockPush).toHaveBeenCalledWith(
      '/clusters/cluster-1/nodes/node-id-1',
    );
  });

  it('should render multiple devices', () => {
    const devices = [
      makeDevice({ gpuUuid: 'gpu-0', gpuId: '0' }),
      makeDevice({ gpuUuid: 'gpu-1', gpuId: '1', hostname: 'node-host-2' }),
    ];
    render(
      <GpuDeviceMetricsGrid
        devices={devices}
        nodesByHostname={new Map()}
        isFetching={false}
      />,
      { wrapper },
    );
    expect(screen.getByText('gpu-device-0')).toBeInTheDocument();
    expect(screen.getByText('gpu-device-1')).toBeInTheDocument();
    expect(screen.getAllByTestId('stats-chart')).toHaveLength(6);
  });
});
