// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen, waitFor } from '@testing-library/react';

import { listWorkloads } from '@/services/app/workloads';
import { getAims } from '@/services/app/aims';

import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

import ChatPage from '@/pages/chat';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';
import { mockAims } from '@/__mocks__/services/app/aims.data';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';

vi.mock('@/services/app/workloads', () => ({
  listWorkloads: vi.fn(),
}));

vi.mock('@/services/app/aims', () => ({
  getAims: vi.fn(),
}));

vi.mock('@/hooks/useSystemToast', () => ({
  __esModule: true,
  default: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

// Mock ChatView as a simple component
vi.mock('@/components/features/chat/ChatView', () => ({
  ChatView: ({ workloads }: { workloads: Workload[] }) => (
    <div data-testid="chat-view">
      <div data-testid="workload-count">{workloads.length}</div>
      {workloads.map((workload) => (
        <div key={workload.id} data-testid={`workload-${workload.id}`}>
          {workload.displayName}
        </div>
      ))}
    </div>
  ),
}));

describe('Chat Page', () => {
  // Create enhanced workloads with userInputs.canonicalName to match AIMs
  // mockAims contains:
  // - mockAims[0]: meta-llama/llama-2-7b with ['llm', 'text-generation', 'chat'] tags
  // - mockAims[1]: stable-diffusion-xl with ['image-generation', 'diffusion'] tags (no chat)
  // - mockAims[2]: detection-model with ['vision', 'object-detection'] tags (no chat)
  const chatWorkloads: Workload[] = [
    {
      ...mockWorkloads[0], // Llama 7B Inference - RUNNING INFERENCE workload
      userInputs: {
        canonicalName: 'meta-llama/llama-2-7b', // matches mockAims[0] (has chat tag)
      },
    },
    {
      ...mockWorkloads[1], // SDXL Download - convert to INFERENCE and RUNNING to be eligible for chat filtering
      type: WorkloadType.INFERENCE,
      status: WorkloadStatus.RUNNING,
      userInputs: {
        canonicalName: 'stable-diffusion-xl', // matches mockAims[1] (no chat tag - should be filtered out)
      },
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (listWorkloads as Mock).mockResolvedValue(chatWorkloads);
    (getAims as Mock).mockResolvedValue(mockAims);
  });

  it('renders the chat page', async () => {
    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });
  });

  it('loads workloads and aims with correct parameters', async () => {
    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledWith('project1', {
        type: [WorkloadType.INFERENCE],
        status: [WorkloadStatus.RUNNING],
      });
      expect(getAims).toHaveBeenCalledWith('project1');
    });
  });

  it('filters workloads to only show chat models', async () => {
    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    // Wait for both queries to complete and filtering to happen
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
      expect(getAims).toHaveBeenCalled();
    });

    // Verify ChatView is rendered with filtered workloads
    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    // Only 1 workload should be passed to ChatView (the one matching llama-2-7b with chat tag)
    // chatWorkloads[0] has canonicalName 'llama-2-7b' which matches mockAims[0] with chat tag
    // chatWorkloads[1] has canonicalName 'stable-diffusion-xl' which matches mockAims[1] without chat tag
    expect(screen.getByTestId('workload-count')).toHaveTextContent('1');
    expect(screen.getByTestId('workload-workload-1')).toBeInTheDocument();
    expect(screen.queryByTestId('workload-workload-2')).not.toBeInTheDocument();
  });

  it('filters out workloads without chat tag in associated aim', async () => {
    // Test with workloads that have only non-chat models
    const nonChatWorkloads = [chatWorkloads[1]]; // Only stable-diffusion-xl (no chat tag)
    (listWorkloads as Mock).mockResolvedValue(nonChatWorkloads);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
      expect(getAims).toHaveBeenCalled();
    });

    // Verify ChatView is rendered but with no workloads
    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    // No workloads should be passed to ChatView since none have chat tags
    expect(screen.getByTestId('workload-count')).toHaveTextContent('0');
  });

  it('handles aims loading error', async () => {
    const mockError = new Error('Failed to load AIMs');
    (getAims as Mock).mockRejectedValue(mockError);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(getAims).toHaveBeenCalled();
    });

    // ChatView should still render with empty workloads
    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });
    expect(screen.getByTestId('workload-count')).toHaveTextContent('0');
  });

  it('handles workloads loading error', async () => {
    const mockError = new Error('Failed to load workloads');
    (listWorkloads as Mock).mockRejectedValue(mockError);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
    });

    // ChatView should still render with empty workloads
    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });
    expect(screen.getByTestId('workload-count')).toHaveTextContent('0');
  });

  it('shows empty chat workloads when no chat models are available', async () => {
    // Use only the non-chat AIM from mockAims (stable-diffusion-xl)
    const aimsWithoutChat = [mockAims[1]]; // stable-diffusion-xl with no chat tag

    (getAims as Mock).mockResolvedValue(aimsWithoutChat);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
      expect(getAims).toHaveBeenCalled();
    });

    // Verify ChatView renders with no workloads
    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    expect(screen.getByTestId('workload-count')).toHaveTextContent('0');
  });

  it('shows no workloads when aims array is empty', async () => {
    (getAims as Mock).mockResolvedValue([]);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
      expect(getAims).toHaveBeenCalled();
    });

    // Verify ChatView renders with no workloads
    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    expect(screen.getByTestId('workload-count')).toHaveTextContent('0');
  });

  it('shows all matching workloads when multiple chat models are available', async () => {
    // Create a third workload that also matches a chat AIM
    const multipleWorkloads = [
      ...chatWorkloads,
      {
        ...mockWorkloads[3], // Model fine-tuning - convert to INFERENCE and RUNNING
        type: WorkloadType.INFERENCE,
        status: WorkloadStatus.RUNNING,
        userInputs: {
          canonicalName: 'meta-llama/llama-2-7b', // Also matches the chat AIM
        },
      },
    ];

    (listWorkloads as Mock).mockResolvedValue(multipleWorkloads);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
      expect(getAims).toHaveBeenCalled();
    });

    // Verify ChatView receives multiple workloads
    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    // Should have 2 workloads (both matching meta-llama/llama-2-7b chat AIM)
    expect(screen.getByTestId('workload-count')).toHaveTextContent('2');
  });

  it('includes deployed finetuned models with chat capability', async () => {
    const workloadsWithCapabilities: Workload[] = [
      {
        ...mockWorkloads[0],
        capabilities: ['chat'],
        userInputs: {
          canonicalName: 'finetuned-model',
        },
      },
    ];

    (listWorkloads as Mock).mockResolvedValue(workloadsWithCapabilities);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
      expect(getAims).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    expect(screen.getByTestId('workload-count')).toHaveTextContent('1');
    expect(screen.getByTestId('workload-workload-1')).toBeInTheDocument();
  });

  it('avoids duplicates when deployed AIM also has chat capability', async () => {
    const workloadsWithBoth: Workload[] = [
      {
        ...mockWorkloads[0],
        capabilities: ['chat'],
        userInputs: {
          canonicalName: 'meta-llama/llama-2-7b', // Matches AIM with chat tag
        },
      },
    ];

    (listWorkloads as Mock).mockResolvedValue(workloadsWithBoth);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
      expect(getAims).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    expect(screen.getByTestId('workload-count')).toHaveTextContent('1');
  });

  it('combines deployed AIMs and finetuned models without duplicates', async () => {
    const mixedWorkloads: Workload[] = [
      {
        ...mockWorkloads[0],
        userInputs: {
          canonicalName: 'meta-llama/llama-2-7b', // Matches AIM with chat tag
        },
      },
      {
        ...mockWorkloads[1],
        type: WorkloadType.INFERENCE,
        status: WorkloadStatus.RUNNING,
        capabilities: ['chat'],
        userInputs: {
          canonicalName: 'finetuned-model', // No matching AIM, but has chat capability
        },
      },
    ];

    (listWorkloads as Mock).mockResolvedValue(mixedWorkloads);

    await act(async () => {
      render(<ChatPage />, { wrapper });
    });

    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalled();
      expect(getAims).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    });

    expect(screen.getByTestId('workload-count')).toHaveTextContent('2');
  });
});
