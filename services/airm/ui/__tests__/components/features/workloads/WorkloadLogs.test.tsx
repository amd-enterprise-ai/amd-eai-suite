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

import { getWorkloadLogs } from '@/services/app/workloads';

import {
  WorkloadStatus,
  WorkloadType,
  LogLevel,
} from '@/types/enums/workloads';
import {
  Workload,
  LogEntry,
  WorkloadLogResponse,
  WorkloadLogPagination,
} from '@/types/workloads';

import WorkloadLogs from '@/components/features/workloads/WorkloadLogs';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

import { useWorkloadLogsStream } from '@/hooks/useWorkloadLogsStream';

// Mock the streaming hook
vi.mock('@/hooks/useWorkloadLogsStream');

// Mock the API services
vi.mock('@/services/app/workloads', () => ({
  getWorkloadLogs: vi.fn(),
}));

// Mock useSystemToast for testing
vi.mock('@/hooks/useSystemToast', () => ({
  __esModule: true,
  default: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

// Mock lodash throttle
vi.mock('lodash', () => ({
  throttle: vi.fn((fn) => {
    fn.cancel = vi.fn();
    return fn;
  }),
}));

describe('WorkloadLogs', () => {
  const mockWorkload: Workload = {
    id: 'workload-1',
    name: 'Test Workload',
    displayName: 'Test Workload Display',
    status: WorkloadStatus.RUNNING,
    type: WorkloadType.INFERENCE,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z',
    createdBy: 'test-user',
    chartId: 'chart-1',
    clusterId: 'cluster-1',
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-01T00:00:00Z',
      status: 'HEALTHY' as any,
    },
    allocatedResources: {
      gpuCount: 1,
      vram: 2147483648.0,
    },
  };

  const mockLogEntries: LogEntry[] = [
    {
      timestamp: '2023-01-01T10:00:00Z',
      level: LogLevel.INFO,
      message: 'Application started successfully',
    },
    {
      timestamp: '2023-01-01T10:01:00Z',
      level: LogLevel.WARNING,
      message: 'Low memory warning',
    },
    {
      timestamp: '2023-01-01T10:02:00Z',
      level: LogLevel.ERROR,
      message: 'Connection timeout error',
    },
  ];

  const mockPagination: WorkloadLogPagination = {
    hasMore: true,
    pageToken: '2023-01-01T09:59:00Z',
    totalReturned: 3,
  };

  const mockWorkloadLogsResponse: WorkloadLogResponse = {
    logs: mockLogEntries,
    pagination: mockPagination,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (getWorkloadLogs as Mock).mockResolvedValue(mockWorkloadLogsResponse);

    // Reset the streaming hook mock
    vi.mocked(useWorkloadLogsStream).mockReturnValue({
      logs: [] as LogEntry[],
      isLoading: false,
      isStreaming: false,
      error: null as string | null,
      startStreaming: vi.fn(),
      stopStreaming: vi.fn(),
      clearLogs: vi.fn(),
    });
  });

  it('renders workload logs when workload is provided', async () => {
    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    // Wait for the logs to load
    await waitFor(() => {
      expect(getWorkloadLogs).toHaveBeenCalled();
    });

    // Check workload description is displayed
    expect(
      screen.getByText('list.actions.logs.modal.description'),
    ).toBeInTheDocument();

    // Check streaming toggle is present
    expect(
      screen.getByText('list.actions.logs.modal.streaming'),
    ).toBeInTheDocument();

    // Check that logs are displayed
    await waitFor(() => {
      expect(
        screen.getByText('Application started successfully'),
      ).toBeInTheDocument();
    });
    expect(screen.getByText('Low memory warning')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout error')).toBeInTheDocument();
  });

  it('shows workload not found message when no workload is provided', () => {
    render(<WorkloadLogs workload={undefined} isOpen={true} />, { wrapper });

    expect(
      screen.getByText('list.actions.logs.modal.workloadNotFound'),
    ).toBeInTheDocument();
  });

  it('shows loading state when logs are being fetched', async () => {
    (getWorkloadLogs as Mock).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000)),
    );

    render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, { wrapper });

    expect(screen.getByTestId('workload-logs-loading')).toBeInTheDocument();
  });

  it('displays log entries with correct formatting', async () => {
    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    // Wait for the logs to load and be displayed
    await waitFor(() => {
      expect(getWorkloadLogs).toHaveBeenCalled();
    });

    // Wait for the logs to be rendered in the DOM
    await waitFor(() => {
      expect(
        screen.getByText('Application started successfully'),
      ).toBeInTheDocument();
    });

    // Check that all log messages are displayed
    expect(screen.getByText('Low memory warning')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout error')).toBeInTheDocument();

    // Check that log levels are displayed (they are rendered in lowercase, but styled with uppercase CSS)
    expect(
      screen.getByText((content, element) => {
        return element?.textContent === '[info]';
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText((content, element) => {
        return element?.textContent === '[warning]';
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText((content, element) => {
        return element?.textContent === '[error]';
      }),
    ).toBeInTheDocument();
  });

  it('calls getWorkloadLogs with correct parameters', async () => {
    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getWorkloadLogs).toHaveBeenCalledWith('workload-1', {
        direction: 'backward',
        pageToken: undefined,
        level: undefined,
      });
    });
  });
  it('handles streaming mode toggle', async () => {
    const mockStartStreaming = vi.fn();
    const mockStopStreaming = vi.fn();
    const mockClearLogs = vi.fn();

    vi.mocked(useWorkloadLogsStream).mockReturnValue({
      logs: [mockLogEntries[0]],
      isLoading: false,
      isStreaming: false,
      error: null,
      startStreaming: mockStartStreaming,
      stopStreaming: mockStopStreaming,
      clearLogs: mockClearLogs,
    });

    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    // Find the streaming toggle switch
    const streamingSwitch = screen.getByRole('switch');

    // Toggle streaming mode
    await act(async () => {
      fireEvent.click(streamingSwitch);
    });

    // Verify startStreaming was called (with delay)
    await waitFor(
      () => {
        expect(mockStartStreaming).toHaveBeenCalled();
      },
      { timeout: 200 },
    );
  });

  it('handles pagination when scrolling', async () => {
    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getWorkloadLogs).toHaveBeenCalled();
    });

    // Find the logs container by test ID
    const logsContainer = screen.getByTestId('workload-logs-container');

    // Mock scroll properties using a spy on the scroll event handler
    const scrollSpy = vi.fn();
    logsContainer.addEventListener('scroll', scrollSpy);

    // Simulate scroll event with mocked values
    Object.defineProperty(logsContainer, 'scrollTop', {
      configurable: true,
      writable: true,
      value: 450,
    });
    Object.defineProperty(logsContainer, 'scrollHeight', {
      configurable: true,
      writable: true,
      value: 1000,
    });
    Object.defineProperty(logsContainer, 'clientHeight', {
      configurable: true,
      writable: true,
      value: 400,
    });

    // Simulate scroll event
    await act(async () => {
      fireEvent.scroll(logsContainer);
    });

    // The main verification is that the component handles scroll without errors
    expect(getWorkloadLogs).toHaveBeenCalled();
  });

  it('handles empty logs response', async () => {
    const emptyResponse: WorkloadLogResponse = {
      logs: [],
      pagination: {
        hasMore: false,
        pageToken: undefined,
        totalReturned: 0,
      },
    };

    (getWorkloadLogs as Mock).mockResolvedValue(emptyResponse);

    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getWorkloadLogs).toHaveBeenCalled();
    });

    // Should show workload description but no log entries
    expect(
      screen.getByText('list.actions.logs.modal.description'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Application started successfully'),
    ).not.toBeInTheDocument();
  });

  it('cleans up when isOpen becomes false', async () => {
    const mockStopStreaming = vi.fn();
    const mockClearLogs = vi.fn();

    vi.mocked(useWorkloadLogsStream).mockReturnValue({
      logs: [],
      isLoading: false,
      isStreaming: true,
      error: null,
      startStreaming: vi.fn(),
      stopStreaming: mockStopStreaming,
      clearLogs: mockClearLogs,
    });

    const { rerender } = await act(async () => {
      return render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getWorkloadLogs).toHaveBeenCalled();
    });

    // Close the component
    await act(async () => {
      rerender(<WorkloadLogs workload={mockWorkload} isOpen={false} />);
    });

    // Verify cleanup was called
    expect(mockStopStreaming).toHaveBeenCalled();
    expect(mockClearLogs).toHaveBeenCalled();
  });

  it('only enables query when workload exists and component is open', () => {
    // Test with workload but component closed
    const { rerender } = render(
      <WorkloadLogs workload={mockWorkload} isOpen={false} />,
      { wrapper },
    );

    expect(getWorkloadLogs).not.toHaveBeenCalled();

    // Test with component open but no workload
    rerender(<WorkloadLogs workload={undefined} isOpen={true} />);

    expect(getWorkloadLogs).not.toHaveBeenCalled();

    // Test with both workload and component open
    rerender(<WorkloadLogs workload={mockWorkload} isOpen={true} />);

    // Now it should be called
    expect(getWorkloadLogs).toHaveBeenCalled();
  });

  it('handles API errors gracefully', async () => {
    const mockError = new Error('API Error');
    (getWorkloadLogs as Mock).mockRejectedValue(mockError);

    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    // The component should handle the error gracefully
    await waitFor(() => {
      expect(getWorkloadLogs).toHaveBeenCalled();
    });

    // Component should still render without crashing
    expect(
      screen.getByText('list.actions.logs.modal.description'),
    ).toBeInTheDocument();
  });

  it('handles streaming errors', async () => {
    vi.mocked(useWorkloadLogsStream).mockReturnValue({
      logs: [] as LogEntry[],
      isLoading: false,
      isStreaming: false,
      error: 'Streaming connection failed' as string,
      startStreaming: vi.fn(),
      stopStreaming: vi.fn(),
      clearLogs: vi.fn(),
    });

    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    // Component should handle streaming error gracefully
    expect(
      screen.getByText('list.actions.logs.modal.description'),
    ).toBeInTheDocument();
  });

  it('auto-scrolls to bottom when new streaming logs arrive', async () => {
    const scrollToSpy = vi.fn();
    Object.defineProperty(HTMLElement.prototype, 'scrollTop', {
      configurable: true,
      set: scrollToSpy,
    });
    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
      configurable: true,
      get: () => 1000,
    });

    vi.mocked(useWorkloadLogsStream).mockReturnValue({
      logs: [mockLogEntries[0]],
      isLoading: false,
      isStreaming: true,
      error: null,
      startStreaming: vi.fn(),
      stopStreaming: vi.fn(),
      clearLogs: vi.fn(),
    });

    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    // The component should render with streaming mode
    expect(
      screen.getByText('list.actions.logs.modal.description'),
    ).toBeInTheDocument();
  });

  it('displays pagination loading indicator', async () => {
    // Mock a scenario where pagination is loading
    const firstResponse: WorkloadLogResponse = {
      logs: mockLogEntries.slice(0, 2),
      pagination: {
        hasMore: true,
        pageToken: '2023-01-01T09:59:00Z',
        totalReturned: 2,
      },
    };

    (getWorkloadLogs as Mock).mockResolvedValue(firstResponse);

    await act(async () => {
      render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getWorkloadLogs).toHaveBeenCalled();
    });

    // Initial logs should be displayed
    await waitFor(() => {
      expect(
        screen.getByText('Application started successfully'),
      ).toBeInTheDocument();
    });

    // The test mainly verifies that the component can handle pagination states
    expect(
      screen.getByText('list.actions.logs.modal.description'),
    ).toBeInTheDocument();
  });

  // Log Level filtering tests
  describe('Log Level Filtering', () => {
    it('shows log level dropdown', async () => {
      await act(async () => {
        render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
          wrapper,
        });
      });

      // Should show the log level filter dropdown
      expect(
        screen.getByText('list.actions.logs.modal.logLevelFilter.label'),
      ).toBeInTheDocument();

      // Should show the "All levels" option by default
      expect(
        screen.getByText('list.actions.logs.modal.logLevelFilter.allLevels'),
      ).toBeInTheDocument();
    });

    it('displays all available log levels in dropdown', async () => {
      await act(async () => {
        render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
          wrapper,
        });
      });

      // Find and click the log level dropdown
      const dropdown = screen.getByRole('button', {
        name: /list\.actions\.logs\.modal\.logLevelFilter\.label/i,
      });

      await act(async () => {
        fireEvent.click(dropdown);
      });

      // Check that all log levels are available
      expect(screen.getByRole('option', { name: 'TRACE' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'DEBUG' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'INFO' })).toBeInTheDocument();
      expect(
        screen.getByRole('option', { name: 'UNKNOWN' }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('option', { name: 'WARNING' }),
      ).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'ERROR' })).toBeInTheDocument();
      expect(
        screen.getByRole('option', { name: 'CRITICAL' }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('option', {
          name: 'list.actions.logs.modal.logLevelFilter.allLevels',
        }),
      ).toBeInTheDocument();
    });

    it('filters logs by selected log level', async () => {
      await act(async () => {
        render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
          wrapper,
        });
      });

      // Initial call should not have log level filter
      await waitFor(() => {
        expect(getWorkloadLogs).toHaveBeenCalledWith('workload-1', {
          direction: 'backward',
          pageToken: undefined,
          level: undefined,
        });
      });

      // Find and click the log level dropdown
      const dropdown = screen.getByRole('button', {
        name: /list\.actions\.logs\.modal\.logLevelFilter\.label/i,
      });

      await act(async () => {
        fireEvent.click(dropdown);
      });

      // Select ERROR level from the dropdown
      const errorOption = screen.getByRole('option', { name: 'ERROR' });
      await act(async () => {
        fireEvent.click(errorOption);
      });

      // Should call getWorkloadLogs with log level filter
      await waitFor(() => {
        expect(getWorkloadLogs).toHaveBeenCalledWith('workload-1', {
          direction: 'backward',
          pageToken: undefined,
          level: LogLevel.ERROR,
        });
      });
    });

    it('clears logs when log level filter changes', async () => {
      await act(async () => {
        render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
          wrapper,
        });
      });

      // Wait for initial logs to load
      await waitFor(() => {
        expect(
          screen.getByText('Application started successfully'),
        ).toBeInTheDocument();
      });

      // Change log level filter
      const dropdown = screen.getByRole('button', {
        name: /list\.actions\.logs\.modal\.logLevelFilter\.label/i,
      });

      await act(async () => {
        fireEvent.click(dropdown);
      });

      const warningOption = screen.getByRole('option', { name: 'WARNING' });
      await act(async () => {
        fireEvent.click(warningOption);
      });

      // Logs should be cleared and reloaded with log level filter
      await waitFor(() => {
        expect(getWorkloadLogs).toHaveBeenCalledWith('workload-1', {
          direction: 'backward',
          pageToken: undefined,

          level: LogLevel.WARNING,
        });
      });
    });

    it('restarts streaming when log level filter changes during streaming', async () => {
      const mockStartStreaming = vi.fn();
      const mockStopStreaming = vi.fn();
      const mockClearLogs = vi.fn();

      vi.mocked(useWorkloadLogsStream).mockReturnValue({
        logs: [mockLogEntries[0]],
        isLoading: false,
        isStreaming: true,
        error: null,
        startStreaming: mockStartStreaming,
        stopStreaming: mockStopStreaming,
        clearLogs: mockClearLogs,
      });

      await act(async () => {
        render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
          wrapper,
        });
      });

      // Enable streaming mode first
      const streamingSwitch = screen.getByRole('switch');
      await act(async () => {
        fireEvent.click(streamingSwitch);
      });

      // Now change log level filter
      const dropdown = screen.getByRole('button', {
        name: /list\.actions\.logs\.modal\.logLevelFilter\.label/i,
      });

      await act(async () => {
        fireEvent.click(dropdown);
      });

      const infoOption = screen.getByRole('option', { name: 'INFO' });
      await act(async () => {
        fireEvent.click(infoOption);
      });

      // Should stop and restart streaming
      await waitFor(() => {
        expect(mockStopStreaming).toHaveBeenCalled();
        expect(mockClearLogs).toHaveBeenCalled();
      });

      // Should restart streaming after delay
      await waitFor(
        () => {
          expect(mockStartStreaming).toHaveBeenCalled();
        },
        { timeout: 200 },
      );
    });

    it('includes log level in streaming params', async () => {
      await act(async () => {
        render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
          wrapper,
        });
      });

      // Select a log level first
      const dropdown = screen.getByRole('button', {
        name: /list\.actions\.logs\.modal\.logLevelFilter\.label/i,
      });

      await act(async () => {
        fireEvent.click(dropdown);
      });

      const debugOption = screen.getByRole('option', { name: 'DEBUG' });
      await act(async () => {
        fireEvent.click(debugOption);
      });

      // The streaming hook should be called with log level in params
      expect(useWorkloadLogsStream).toHaveBeenCalledWith({
        workloadId: 'workload-1',
        params: expect.objectContaining({
          level: LogLevel.DEBUG,
        }),
        autoStart: false,
      });
    });

    it('resets log level filter during cleanup', async () => {
      const { rerender } = await act(async () => {
        return render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(getWorkloadLogs).toHaveBeenCalled();
      });

      // Select a log level filter
      const dropdown = screen.getByRole('button', {
        name: /list\.actions\.logs\.modal\.logLevelFilter\.label/i,
      });

      await act(async () => {
        fireEvent.click(dropdown);
      });

      const traceOption = screen.getByRole('option', { name: 'TRACE' });
      await act(async () => {
        fireEvent.click(traceOption);
      });

      // Close the component
      await act(async () => {
        rerender(<WorkloadLogs workload={mockWorkload} isOpen={false} />);
      });

      // Reopen the component
      await act(async () => {
        rerender(<WorkloadLogs workload={mockWorkload} isOpen={true} />);
      });

      // Should be reset to default (no log level filter)
      await waitFor(() => {
        expect(getWorkloadLogs).toHaveBeenCalledWith('workload-1', {
          direction: 'backward',
          pageToken: undefined,

          level: undefined,
        });
      });
    });

    it('clears log level filter when selecting "All levels" option', async () => {
      await act(async () => {
        render(<WorkloadLogs workload={mockWorkload} isOpen={true} />, {
          wrapper,
        });
      });

      // First select a specific log level
      const dropdown = screen.getByRole('button', {
        name: /list\.actions\.logs\.modal\.logLevelFilter\.label/i,
      });

      await act(async () => {
        fireEvent.click(dropdown);
      });

      const errorOption = screen.getByRole('option', { name: 'ERROR' });
      await act(async () => {
        fireEvent.click(errorOption);
      });

      await waitFor(() => {
        expect(getWorkloadLogs).toHaveBeenCalledWith('workload-1', {
          direction: 'backward',
          pageToken: undefined,
          level: LogLevel.ERROR,
        });
      });

      // Now select "All levels" to clear the filter
      await act(async () => {
        fireEvent.click(dropdown);
      });

      const allLevelsOption = screen.getByRole('option', {
        name: 'list.actions.logs.modal.logLevelFilter.allLevels',
      });
      await act(async () => {
        fireEvent.click(allLevelsOption);
      });

      // Should call getWorkloadLogs without log level filter
      await waitFor(() => {
        expect(getWorkloadLogs).toHaveBeenCalledWith('workload-1', {
          direction: 'backward',
          pageToken: undefined,

          level: undefined,
        });
      });
    });
  });
});
