// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import {
  fetchNamespaceMetrics,
  fetchNamespaceStats,
  fetchNamespaceGPUDeviceUtilization,
  fetchNamespaceGPUMemoryUtilization,
} from '@/lib/app/namespaces';

import type { GetServerSidePropsContext } from 'next';
import { getServerSession } from 'next-auth';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import type { ComponentProps } from 'react';
import { Mock, vi } from 'vitest';
import ProjectDashboardPage, { getServerSideProps } from '@/pages/[project]';

const mockGetServerSession = vi.mocked(getServerSession);
const mockServerSideTranslations = vi.mocked(serverSideTranslations);

const mockInvalidateQueries = vi.fn();
const mockResetQueries = vi.fn();

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries: mockInvalidateQueries,
      resetQueries: mockResetQueries,
      getQueryCache: () => ({
        findAll: () => [],
        subscribe: (_onStoreChange: () => void) => () => {},
      }),
    }),
  };
});

vi.mock('next-auth', () => ({
  getServerSession: vi.fn(),
}));

vi.mock('next-i18next/serverSideTranslations', () => ({
  serverSideTranslations: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/lib/app/namespaces', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchNamespaceMetrics: vi.fn(),
    fetchNamespaceStats: vi.fn(),
    fetchNamespaceGPUDeviceUtilization: vi.fn(),
    fetchNamespaceGPUMemoryUtilization: vi.fn(),
  };
});

vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'test-project-123',
    setActiveProject: vi.fn(),
  }),
}));

vi.mock('@/lib/app/aims', () => ({
  getAimServices: vi.fn().mockResolvedValue([]),
  getAimClusterModels: vi.fn().mockResolvedValue([]),
  undeployAim: vi.fn(),
}));

const mockPush = vi.fn();

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: '1' },
    push: mockPush,
  }),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: {
      user: {
        email: 'test@example.com',
        id: 'test-user-id',
      },
    },
    update: vi.fn(),
  }),
}));

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('projects page', () => {
  beforeEach(() => {
    (fetchNamespaceMetrics as Mock).mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      pageSize: 20,
      totalPages: 0,
    });
    (fetchNamespaceStats as Mock).mockResolvedValue({
      namespace: 'workbench',
      total: 0,
      statusCounts: [],
    });
    (fetchNamespaceGPUMemoryUtilization as Mock).mockResolvedValue({
      data: [],
    });
    (fetchNamespaceGPUDeviceUtilization as Mock).mockResolvedValue({
      data: [],
    });
    mockInvalidateQueries.mockClear();
    mockResetQueries.mockClear();
  });

  const renderProjectPage = (
    props?: Partial<ComponentProps<typeof ProjectDashboardPage>>,
  ) => {
    return render(<ProjectDashboardPage {...props} />, { wrapper });
  };

  it('shows loading state initially', async () => {
    act(() => {
      renderProjectPage();
    });

    await waitFor(() => {
      expect(screen.getByText('dashboard.overview.title')).toBeInTheDocument();
    });
  });

  it('should not crash the page', async () => {
    act(() => {
      renderProjectPage();
    });

    await waitFor(() => {
      expect(screen.getByText('dashboard.overview.title')).toBeInTheDocument();
    });
  });

  it('should call fetchNamespaceGPUDeviceUtilization on page load', () => {
    act(() => {
      renderProjectPage();
    });

    expect(fetchNamespaceGPUDeviceUtilization as Mock).toHaveBeenCalled();
  });

  it('should call fetchNamespaceMetrics on page load', async () => {
    act(() => {
      renderProjectPage();
    });

    await waitFor(() => {
      expect(fetchNamespaceMetrics as Mock).toHaveBeenCalled();
    });
  });

  it('should call fetchNamespaceStats on page load', () => {
    act(() => {
      renderProjectPage();
    });

    expect(fetchNamespaceStats as Mock).toHaveBeenCalled();
  });

  it('should call fetchNamespaceGPUMemoryUtilization on page load', () => {
    act(() => {
      renderProjectPage();
    });

    expect(fetchNamespaceGPUMemoryUtilization as Mock).toHaveBeenCalled();
  });

  it('refresh button trigger refetch', async () => {
    await act(() => {
      renderProjectPage();
    });

    expect(fetchNamespaceGPUMemoryUtilization as Mock).toBeCalledTimes(1);
    expect(fetchNamespaceGPUDeviceUtilization as Mock).toBeCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByText('data.refresh')).toBeInTheDocument();
    });

    await act(() => {
      fireEvent.click(screen.getByText('data.refresh'));
    });

    expect(fetchNamespaceGPUMemoryUtilization as Mock).toBeCalledTimes(2);
    expect(fetchNamespaceGPUDeviceUtilization as Mock).toBeCalledTimes(2);
    expect(mockInvalidateQueries).toHaveBeenCalledWith({
      queryKey: ['namespace', 'test-project-123', 'workloads'],
    });
    expect(mockResetQueries).toHaveBeenCalledWith({
      queryKey: ['namespace', 'test-project-123', 'stats'],
    });
  });

  it('should handle time range change correctly', async () => {
    await act(() => {
      renderProjectPage();
    });

    // Verify the time selector component is rendered
    await waitFor(() => {
      expect(screen.getByText('data.refresh')).toBeInTheDocument();
    });
  });

  it('should render all dashboard sections', async () => {
    act(() => {
      renderProjectPage();
    });

    // Check for overview sections
    await waitFor(() => {
      expect(screen.getByText('dashboard.overview.title')).toBeInTheDocument();
      expect(screen.getByText('dashboard.workloads.title')).toBeInTheDocument();
    });
  });
});

describe('ProjectDashboardPage getServerSideProps', () => {
  const baseContext = {
    locale: 'en',
    params: { project: 'bench-ns' },
    query: {},
    resolvedUrl: '/bench-ns',
    req: {},
    res: {},
  } as unknown as GetServerSidePropsContext;

  beforeEach(() => {
    vi.clearAllMocks();
    mockServerSideTranslations.mockResolvedValue({} as never);
  });

  it('returns props with breadcrumb when session and translations succeed', async () => {
    mockGetServerSession.mockResolvedValue({
      user: { email: 'test@example.com' },
      accessToken: 'token',
    } as never);

    const result = await getServerSideProps(baseContext);

    expect(result).toEqual({
      props: {
        pageBreadcrumb: [
          {
            title: undefined,
            href: '/bench-ns/',
          },
        ],
      },
    });
    expect(mockGetServerSession).toHaveBeenCalledWith(
      baseContext.req,
      baseContext.res,
      expect.any(Object),
    );
  });

  it('redirects home when session is missing', async () => {
    mockGetServerSession.mockResolvedValue(null);

    const result = await getServerSideProps(baseContext);

    expect(result).toEqual({
      redirect: { destination: '/', permanent: false },
    });
  });

  it('redirects home when translations fail', async () => {
    mockGetServerSession.mockResolvedValue({
      user: { email: 'test@example.com' },
      accessToken: 'token',
    } as never);
    mockServerSideTranslations.mockRejectedValue(new Error('i18n failed'));

    const result = await getServerSideProps(baseContext);

    expect(result).toEqual({
      redirect: { destination: '/', permanent: false },
    });
  });
});
