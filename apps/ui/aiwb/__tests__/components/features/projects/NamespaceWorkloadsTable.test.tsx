// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';

import { fetchNamespaceMetrics } from '@/lib/app/namespaces';
import {
  getAimServices,
  getAimClusterModels,
  resolveAIMServiceDisplay,
  undeployAim,
} from '@/lib/app/aims';
import { deleteWorkload } from '@/lib/app/workloads';

import { ResourceType } from '@amdenterpriseai/types';
import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import type { ResourceMetrics } from '@/types/namespaces';

import { NamespaceWorkloadsTable } from '@/components/features/projects/NamespaceWorkloadsTable';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

vi.mock('@/lib/app/namespaces', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchNamespaceMetrics: vi.fn(),
  };
});

vi.mock('@/lib/app/workloads', () => ({
  deleteWorkload: vi.fn(),
}));

vi.mock('@/lib/app/aims', () => ({
  getAimServices: vi.fn(),
  getAimClusterModels: vi.fn(),
  resolveAIMServiceDisplay: vi.fn(),
  undeployAim: vi.fn(),
}));

const mockPush = vi.fn();
vi.mock('next/router', () => ({
  useRouter: () => ({
    push: mockPush,
    query: {},
    pathname: '/',
    asPath: '/',
  }),
}));

vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  __esModule: true,
  ...(await importOriginal()),
  useSystemToast: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

vi.mock('next-i18next', () => ({
  Trans: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}));

vi.mock('@tabler/icons-react', async (importOriginal) => {
  const actual = (await importOriginal()) ?? {};
  return {
    ...actual,
    IconDotsVertical: () => <span>action-dots</span>,
    IconEye: () => null,
    IconFileText: () => null,
    IconLink: () => null,
    IconMessage: () => null,
    IconTrash: () => null,
  };
});

const createMockResourceMetrics = (
  overrides: Partial<ResourceMetrics> = {},
): ResourceMetrics => ({
  id: 'workload-1',
  name: 'workload-1',
  displayName: 'Test Workload',
  type: WorkloadType.INFERENCE,
  status: WorkloadStatus.RUNNING,
  gpuCount: 1,
  vram: 2 * 1024 * 1024 * 1024,
  createdAt: '2024-01-01T00:00:00Z',
  createdBy: 'test-user',
  resourceType: ResourceType.DEPLOYMENT,
  ...overrides,
});

const mockNamespaceMetricsResponse = {
  data: [
    createMockResourceMetrics({
      id: 'workload-1',
      displayName: 'Regular Workload',
      resourceType: ResourceType.DEPLOYMENT,
    }),
    createMockResourceMetrics({
      id: 'aim-service-1',
      displayName: 'AIM Service',
      resourceType: ResourceType.AIM_SERVICE,
    }),
  ],
  total: 2,
  page: 1,
  pageSize: 20,
  totalPages: 1,
};

describe('NamespaceWorkloadsTable', () => {
  const mockFetchNamespaceMetrics = fetchNamespaceMetrics as Mock;
  const mockGetAimServices = getAimServices as Mock;
  const mockGetAimClusterModels = getAimClusterModels as Mock;
  const mockDeleteWorkload = deleteWorkload as Mock;
  const mockUndeployAim = undeployAim as Mock;
  const mockResolveAIMServiceDisplay = resolveAIMServiceDisplay as Mock;

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchNamespaceMetrics.mockResolvedValue(mockNamespaceMetricsResponse);
    mockGetAimServices.mockResolvedValue([]);
    mockGetAimClusterModels.mockResolvedValue([]);
    mockResolveAIMServiceDisplay.mockImplementation(
      (_service: unknown, _parsedAIMs: unknown[]) => ({
        canonicalName: 'test/model',
        imageVersion: '1.0',
        metric: 'default',
        title: 'Test Model',
        resourceName: 'test-model',
      }),
    );
    Object.defineProperty(window, 'open', {
      writable: true,
      value: vi.fn(),
    });
  });

  it('renders table with loading state then data', async () => {
    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(mockFetchNamespaceMetrics).toHaveBeenCalledWith(
        'test-ns',
        expect.any(Object),
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Regular Workload')).toBeInTheDocument();
      expect(screen.getByText('AIM Service')).toBeInTheDocument();
    });
  });

  it('navigates to workload details when details action is clicked', async () => {
    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Regular Workload')).toBeInTheDocument();
    });

    const row = screen.getByText('Regular Workload').closest('tr');
    expect(row).not.toBeNull();
    const trigger = within(row!).getByRole('button', {
      name: 'list.actions.label',
    });
    await act(async () => {
      fireEvent.click(trigger);
    });

    const detailsAction = await screen.findByTestId('details');
    await act(async () => {
      fireEvent.click(detailsAction);
    });

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith({
        pathname: '/workloads/workload-1',
        search: 'ref=/',
      });
    });
  });

  it('navigates to AIM details when details action is clicked for AIM service', async () => {
    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('AIM Service')).toBeInTheDocument();
    });

    const rows = screen.getAllByRole('row');
    const aimRow = rows.find((r) => r.textContent?.includes('AIM Service'));
    expect(aimRow).toBeDefined();
    const trigger = within(aimRow!).getByRole('button', {
      name: 'list.actions.label',
    });
    await act(async () => {
      fireEvent.click(trigger);
    });

    const detailsAction = await screen.findByTestId('details');
    await act(async () => {
      fireEvent.click(detailsAction);
    });

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith({
        pathname: '/aims/aim-service-1',
        search: 'ref=/',
      });
    });
  });

  it('opens chat in new tab when chat action is clicked', async () => {
    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Regular Workload')).toBeInTheDocument();
    });

    const row = screen.getByText('Regular Workload').closest('tr');
    const trigger = within(row!).getByRole('button', {
      name: 'list.actions.label',
    });
    await act(async () => {
      fireEvent.click(trigger);
    });

    const chatAction = await screen.findByTestId('chat');
    await act(async () => {
      fireEvent.click(chatAction);
    });

    expect(window.open).toHaveBeenCalledWith(
      '/chat?workload=workload-1',
      '_blank',
    );
  });

  it('shows Connect to model action for running AIM workloads', async () => {
    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('AIM Service')).toBeInTheDocument();
    });

    const rows = screen.getAllByRole('row');
    const aimRow = rows.find((r) => r.textContent?.includes('AIM Service'));
    const trigger = within(aimRow!).getByRole('button', {
      name: 'list.actions.label',
    });
    await act(async () => {
      fireEvent.click(trigger);
    });

    await waitFor(() => {
      expect(screen.getByTestId('connect')).toBeInTheDocument();
    });
  });

  it('opens logs modal when logs action is clicked', async () => {
    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Regular Workload')).toBeInTheDocument();
    });

    const row = screen.getByText('Regular Workload').closest('tr');
    const trigger = within(row!).getByRole('button', {
      name: 'list.actions.label',
    });
    await act(async () => {
      fireEvent.click(trigger);
    });

    const logsAction = await screen.findByTestId('logs');
    await act(async () => {
      fireEvent.click(logsAction);
    });

    await waitFor(() => {
      expect(
        screen.getByText('list.actions.logs.modal.title'),
      ).toBeInTheDocument();
    });
  });

  it('opens delete modal when delete action is clicked', async () => {
    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Regular Workload')).toBeInTheDocument();
    });

    const row = screen.getByText('Regular Workload').closest('tr');
    const trigger = within(row!).getByRole('button', {
      name: 'list.actions.label',
    });
    await act(async () => {
      fireEvent.click(trigger);
    });

    const deleteAction = await screen.findByTestId('delete');
    await act(async () => {
      fireEvent.click(deleteAction);
    });

    expect(screen.getByTestId('confirmation-modal')).toBeInTheDocument();
  });

  it('calls deleteWorkload when confirming delete for regular workload', async () => {
    mockDeleteWorkload.mockResolvedValue(undefined);

    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Regular Workload')).toBeInTheDocument();
    });

    const row = screen.getByText('Regular Workload').closest('tr');
    const trigger = within(row!).getByRole('button', {
      name: 'list.actions.label',
    });
    await act(async () => {
      fireEvent.click(trigger);
    });

    const deleteAction = await screen.findByTestId('delete');
    await act(async () => {
      fireEvent.click(deleteAction);
    });

    const confirmButton = await screen.findByTestId('confirm-button');
    await act(async () => {
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(mockDeleteWorkload).toHaveBeenCalledWith('workload-1', 'test-ns');
    });
  });

  it('calls undeployAim when confirming delete for AIM service', async () => {
    mockUndeployAim.mockResolvedValue(undefined);

    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('AIM Service')).toBeInTheDocument();
    });

    const rows = screen.getAllByRole('row');
    const aimRow = rows.find((r) => r.textContent?.includes('AIM Service'));
    const trigger = within(aimRow!).getByRole('button', {
      name: 'list.actions.label',
    });
    await act(async () => {
      fireEvent.click(trigger);
    });

    const deleteAction = await screen.findByTestId('delete');
    await act(async () => {
      fireEvent.click(deleteAction);
    });

    const confirmButton = await screen.findByTestId('confirm-button');
    await act(async () => {
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(mockUndeployAim).toHaveBeenCalledWith('test-ns', 'aim-service-1');
    });
  });

  it('displays AIM canonical name when aimServices and parsedAIMs are loaded', async () => {
    mockGetAimServices.mockResolvedValue([
      {
        id: 'aim-service-1',
        spec: { model: { name: 'test-model' } },
      },
    ]);
    mockGetAimClusterModels.mockResolvedValue([
      { model: 'test-model', resourceName: 'test-model' },
    ]);
    mockResolveAIMServiceDisplay.mockReturnValue({
      canonicalName: 'org/test-model',
      imageVersion: '2.0',
      metric: 'default',
      title: 'Test Model',
      resourceName: 'test-model',
    });

    await act(async () => {
      render(<NamespaceWorkloadsTable namespace="test-ns" />, { wrapper });
    });

    await waitFor(() => {
      expect(mockGetAimServices).toHaveBeenCalled();
      expect(mockGetAimClusterModels).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          /org\/test-model\s+\(2\.0\)\s+\(models:performanceMetrics\.values\.default\)/,
        ),
      ).toBeInTheDocument();
    });
  });
});
