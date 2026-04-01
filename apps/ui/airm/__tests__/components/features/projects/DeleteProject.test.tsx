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

import { deleteProject } from '@/services/app';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';

import { ClusterStatus } from '@amdenterpriseai/types';
import { QuotaStatus } from '@amdenterpriseai/types';
import { ProjectWithResourceAllocation } from '@amdenterpriseai/types';

import DeleteProject from '@/components/features/projects/DeleteProject';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

vi.mock('@/services/app', () => ({
  deleteProject: vi.fn(),
  fetchSubmittableProjects: vi.fn(() =>
    Promise.resolve({
      projects: [
        { id: 'project1', name: 'Project 1' },
        { id: 'project2', name: 'Project 2' },
      ],
    }),
  ),
}));

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('@amdenterpriseai/hooks', () => ({
  useSystemToast: () => {
    const toast = vi.fn() as any;
    toast.success = toastSuccessMock;
    toast.error = toastErrorMock;
    return { toast };
  },
}));

describe('DeleteProject', () => {
  const mockDeleteProject = deleteProject as Mock;

  const mockProject: ProjectWithResourceAllocation = {
    ...generateMockProjects(1)[0],
  };

  beforeEach(() => {
    toastSuccessMock.mockClear();
    toastErrorMock.mockClear();
  });

  it('calls deleteProject when clicked', async () => {
    await act(() => {
      render(<DeleteProject project={mockProject} />, { wrapper });
    });

    await act(async () => {
      const actionButton = screen.getByText('settings.delete.action');
      await fireEvent.click(actionButton);
    });

    await act(async () => {
      const confirmationButton = screen.getByText('actions.confirm.title');
      await fireEvent.click(confirmationButton);
    });

    await waitFor(() => {
      expect(mockDeleteProject).toHaveBeenCalled();
      expect((mockDeleteProject as Mock).mock.calls[0][0]).toBe('1');
      expect(toastSuccessMock).toHaveBeenCalledWith(
        'settings.delete.notification.success',
      );
    });
  });
});
