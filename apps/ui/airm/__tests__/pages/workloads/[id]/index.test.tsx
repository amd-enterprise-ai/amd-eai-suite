// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  getWorkloadMetrics,
  getWorkloadVramUtilization,
  getWorkloadJunctionTemperature,
  getWorkloadPowerUsage,
  deleteWorkload,
} from '@/services/app';

import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import { WorkloadResponse, WorkloadMetricsDetails } from '@/types/workloads';

import { generateClusterNodesMock } from '@/__mocks__/utils/cluster-mock';

import WorkloadDetailPage from '@/pages/workloads/[id]';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';

const mockWorkload: WorkloadResponse = {
  id: 'workload-123',
  type: WorkloadType.INFERENCE,
  name: 'aim-inference-llama3.3-70b-instruct',
  displayName: 'aim-inference-llama3.3-70b-instruct',
  createdBy: 'user@amd.com',
  createdAt: '2025-10-07T19:48:00Z',
  updatedAt: '2025-10-07T19:53:00Z',
  status: WorkloadStatus.RUNNING,
  project: {
    id: 'project-1',
    name: 'Test Project',
    description: '',
    status: 'active' as any,
    statusReason: null,
    clusterId: 'cluster-1',
  },
  projectId: 'project-1',
  clusterId: 'cluster-1',
  allocatedResources: { gpuCount: 2, vram: 128 },
};

const mockWorkloadMetrics: WorkloadMetricsDetails = {
  id: 'workload-123',
  name: 'aim-inference-llama3.3-70b-instruct',
  createdBy: 'user@amd.com',
  createdAt: '2025-10-07T19:48:00Z',
  updatedAt: '2025-10-07T19:53:00Z',
  clusterName: 'demo-cluster',
  clusterId: 'cluster-1',
  nodesInUse: 1,
  gpuDevicesInUse: 2,
  queueTime: 30,
  runningTime: 600,
};

const mockClusterNodes = generateClusterNodesMock(2);

const mockBack = vi.fn();
const mockReplace = vi.fn();
const mockPush = vi.fn();

vi.mock('next-i18next', async (importOriginal) => {
  const actual = await importOriginal<typeof import('next-i18next')>();
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
      i18n: { language: 'en' },
    }),
  };
});

vi.mock('@/services/app', async (importOriginal) => ({
  ...(await importOriginal()),
  deleteWorkload: vi.fn(),
  getWorkloadMetrics: vi.fn(),
  getWorkloadVramUtilization: vi.fn(),
  getWorkloadJunctionTemperature: vi.fn(),
  getWorkloadPowerUsage: vi.fn(),
}));

vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@amdenterpriseai/hooks')>()),
  useSystemToast: () => ({
    toast: { success: vi.fn(), error: vi.fn() },
  }),
}));

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: 'workload-123' },
    isReady: true,
    back: mockBack,
    replace: mockReplace,
    push: mockPush,
  }),
}));

const renderPage = () =>
  render(
    <WorkloadDetailPage
      workload={mockWorkload}
      clusterNodes={mockClusterNodes}
    />,
    { wrapper },
  );

describe('Workload detail page', () => {
  beforeEach(() => {
    vi.mocked(getWorkloadMetrics).mockResolvedValue(mockWorkloadMetrics);
    vi.mocked(getWorkloadVramUtilization).mockResolvedValue({
      gpuDevices: [],
      range: { start: '', end: '' },
    });
    vi.mocked(getWorkloadJunctionTemperature).mockResolvedValue({
      gpuDevices: [],
      range: { start: '', end: '' },
    });
    vi.mocked(getWorkloadPowerUsage).mockResolvedValue({
      gpuDevices: [],
      range: { start: '', end: '' },
    });
    mockBack.mockClear();
    mockReplace.mockClear();
    mockPush.mockClear();
  });

  it('should not crash the page', async () => {
    let container!: HTMLElement;
    await act(async () => {
      const result = renderPage();
      container = result.container;
    });
    await waitFor(() => {
      expect(
        screen.getByText('workloads:details.sections.resourceUtilization'),
      ).toBeInTheDocument();
    });
    expect(container).toBeTruthy();
  });

  it('should render Resource utilization section title', async () => {
    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByText('workloads:details.sections.resourceUtilization'),
      ).toBeInTheDocument();
    });
  });

  it('should render workload name and status', async () => {
    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      const nameElements = screen.getAllByText(
        'aim-inference-llama3.3-70b-instruct',
      );
      expect(nameElements.length).toBeGreaterThan(0);
      expect(nameElements[0]).toBeInTheDocument();
    });
    expect(screen.getByText('status.Running')).toBeInTheDocument();
  });

  it('should render Information section', async () => {
    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByText('workloads:details.sections.workloadInformation'),
      ).toBeInTheDocument();
    });
  });

  it('should show no GPU metrics message when gpu devices data is empty', async () => {
    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByText('workloads:details.fields.noGpuMetrics'),
      ).toBeInTheDocument();
    });
  });

  it('should call getWorkloadMetrics with id from router', async () => {
    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(getWorkloadMetrics as Mock).toHaveBeenCalledWith('workload-123');
    });
  });

  it('should call each GPU metric endpoint with id and time range', async () => {
    await act(async () => {
      renderPage();
    });

    const expectedArgs = [
      'workload-123',
      expect.objectContaining({
        start: expect.any(String),
        end: expect.any(String),
      }),
    ];

    await waitFor(() => {
      expect(getWorkloadVramUtilization as Mock).toHaveBeenCalledWith(
        ...expectedArgs,
      );
      expect(getWorkloadJunctionTemperature as Mock).toHaveBeenCalledWith(
        ...expectedArgs,
      );
      expect(getWorkloadPowerUsage as Mock).toHaveBeenCalledWith(
        ...expectedArgs,
      );
    });
  });

  it('should render back button', async () => {
    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'workloads:details.actions.back' }),
      ).toBeInTheDocument();
    });
  });

  it('should render Delete button', async () => {
    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: 'workloads:details.actions.delete',
        }),
      ).toBeInTheDocument();
    });
  });

  it('should open delete modal and call deleteWorkload on confirm', async () => {
    const user = userEvent.setup();
    vi.mocked(deleteWorkload).mockResolvedValue(undefined);

    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: 'workloads:details.actions.delete',
        }),
      ).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole('button', {
        name: 'workloads:details.actions.delete',
      }),
    );

    await waitFor(() => {
      expect(
        screen.getByText('list.actions.delete.confirmation.title'),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('confirm-button'));

    await waitFor(() => {
      expect(deleteWorkload as Mock).toHaveBeenCalledWith(
        'workload-123',
        expect.any(Object),
      );
    });
  });

  it('should render GPU device metrics with View all metrics button', async () => {
    const gpuNode = mockClusterNodes[0];
    const baseDevice = {
      gpuUuid: 'gpu-0',
      gpuId: '0',
      hostname: gpuNode.name,
    };
    const range = {
      start: '2025-10-07T19:00:00Z',
      end: '2025-10-07T20:00:00Z',
    };

    vi.mocked(getWorkloadVramUtilization).mockResolvedValue({
      gpuDevices: [
        {
          ...baseDevice,
          metric: {
            seriesLabel: 'vram_utilization_pct',
            values: [{ timestamp: '2025-10-07T19:00:00Z', value: 50 }],
          },
        },
      ],
      range,
    });
    vi.mocked(getWorkloadJunctionTemperature).mockResolvedValue({
      gpuDevices: [
        {
          ...baseDevice,
          metric: {
            seriesLabel: 'junction_temperature_c',
            values: [{ timestamp: '2025-10-07T19:00:00Z', value: 60 }],
          },
        },
      ],
      range,
    });
    vi.mocked(getWorkloadPowerUsage).mockResolvedValue({
      gpuDevices: [
        {
          ...baseDevice,
          metric: {
            seriesLabel: 'power_usage_w',
            values: [{ timestamp: '2025-10-07T19:00:00Z', value: 200 }],
          },
        },
      ],
      range,
    });

    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(screen.getByText('gpu-1')).toBeInTheDocument();
      expect(
        screen.getByText(`(${gpuNode.name})`, { exact: false }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', {
          name: 'details.fields.viewAllMetrics',
        }),
      ).toBeInTheDocument();
    });
  });

  it('should navigate to correct node page when View all metrics is clicked', async () => {
    const user = userEvent.setup();
    const gpuNode = mockClusterNodes[0];
    const baseDevice = {
      gpuUuid: 'gpu-0',
      gpuId: '0',
      hostname: gpuNode.name,
    };
    const range = {
      start: '2025-10-07T19:00:00Z',
      end: '2025-10-07T20:00:00Z',
    };

    vi.mocked(getWorkloadVramUtilization).mockResolvedValue({
      gpuDevices: [
        {
          ...baseDevice,
          metric: {
            seriesLabel: 'vram_utilization_pct',
            values: [{ timestamp: '2025-10-07T19:00:00Z', value: 50 }],
          },
        },
      ],
      range,
    });
    vi.mocked(getWorkloadJunctionTemperature).mockResolvedValue({
      gpuDevices: [
        {
          ...baseDevice,
          metric: {
            seriesLabel: 'junction_temperature_c',
            values: [{ timestamp: '2025-10-07T19:00:00Z', value: 60 }],
          },
        },
      ],
      range,
    });
    vi.mocked(getWorkloadPowerUsage).mockResolvedValue({
      gpuDevices: [
        {
          ...baseDevice,
          metric: {
            seriesLabel: 'power_usage_w',
            values: [{ timestamp: '2025-10-07T19:00:00Z', value: 200 }],
          },
        },
      ],
      range,
    });

    await act(async () => {
      renderPage();
    });

    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: 'details.fields.viewAllMetrics',
        }),
      ).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole('button', {
        name: 'details.fields.viewAllMetrics',
      }),
    );

    expect(mockPush).toHaveBeenCalledWith(
      `/clusters/cluster-1/nodes/${gpuNode.id}`,
    );
  });
});
