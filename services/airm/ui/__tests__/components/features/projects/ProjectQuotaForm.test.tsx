// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { generateClustersMock } from '@/__mocks__/utils/cluster-mock';
import { generateMockProjectWithMembers } from '@/__mocks__/utils/project-mock';
import ProjectQuotaForm from '@/components/features/projects/ProjectQuotaForm';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import wrapper from '@/__tests__/ProviderWrapper';
import { updateProject } from '@/services/app/projects';
import { Mock } from 'vitest';

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('@/hooks/useSystemToast', () => {
  const useSystemToast = () => {
    const toast = vi.fn() as any;
    toast.success = toastSuccessMock;
    toast.error = toastErrorMock;
    return { toast };
  };
  return { default: useSystemToast };
});

vi.mock('@/services/app/projects', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    updateProject: vi.fn(),
  };
});

describe('ProjectQuotaForm', () => {
  it('should render correctly', () => {
    const { container } = render(
      <ProjectQuotaForm
        project={generateMockProjectWithMembers(1, 1)}
        cluster={generateClustersMock(1)[0]}
      />,
      { wrapper },
    );
    expect(container).toBeInTheDocument();
  });

  it('edit description field calls update project API correctly', async () => {
    const mockProject = generateMockProjectWithMembers(1, 1);
    const mockCluster = generateClustersMock(1)[0];
    mockProject.clusterId = mockCluster.id;

    act(() => {
      render(<ProjectQuotaForm project={mockProject} cluster={mockCluster} />, {
        wrapper,
      });
    });

    const confirmButton = screen.getByText('settings.form.actions.confirm');
    expect(confirmButton).toBeInTheDocument();
    await fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(updateProject).toHaveBeenCalledWith(
        expect.objectContaining({
          id: mockProject.id,
        }),
      );
    });
  });

  it('call successful toast when resolved successfully', async () => {
    const mockProject = generateMockProjectWithMembers(1, 1);
    const mockCluster = generateClustersMock(1)[0];
    mockProject.clusterId = mockCluster.id;
    (updateProject as Mock).mockResolvedValue(Promise.resolve());

    act(() => {
      render(<ProjectQuotaForm project={mockProject} cluster={mockCluster} />, {
        wrapper,
      });
    });

    const confirmButton = screen.getByText('settings.form.actions.confirm');
    expect(confirmButton).toBeInTheDocument();
    await fireEvent.click(confirmButton);
    await waitFor(() => {
      expect(updateProject).toHaveBeenCalled();
      expect(toastSuccessMock).toHaveBeenCalled();
    });
  });

  it('call error toast when rejected ', async () => {
    const mockProject = generateMockProjectWithMembers(1, 1);
    const mockCluster = generateClustersMock(1)[0];
    mockProject.clusterId = mockCluster.id;
    (updateProject as Mock).mockResolvedValue(Promise.reject({}));

    act(() => {
      render(<ProjectQuotaForm project={mockProject} cluster={mockCluster} />, {
        wrapper,
      });
    });

    const confirmButton = screen.getByText('settings.form.actions.confirm');
    expect(confirmButton).toBeInTheDocument();
    await fireEvent.click(confirmButton);
    await waitFor(() => {
      expect(updateProject).toHaveBeenCalled();
      expect(toastErrorMock).toHaveBeenCalled();
    });
  });
});
