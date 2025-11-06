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

import { createProject } from '@/services/app/projects';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';
import { APIRequestError } from '@/utils/app/errors';

import { ClusterStatus } from '@/types/enums/cluster-status';
import { ProjectWithResourceAllocation } from '@/types/projects';

import CreateProjectModal from '@/components/features/projects/CreateProjectModal';

import wrapper from '@/__tests__/ProviderWrapper';
import userEvent from '@testing-library/user-event';
import { Mock, vi } from 'vitest';
import { generateClustersMock } from '@/__mocks__/utils/cluster-mock';

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
    createProject: vi.fn(),
  };
});

describe('CreateProjectModal', () => {
  const onOpenChange = vi.fn();
  const onProjectCreate = vi.fn();
  const createProjects = (n: number): ProjectWithResourceAllocation[] =>
    generateMockProjects(n);
  const projects = createProjects(1);

  beforeEach(() => {
    toastSuccessMock.mockClear();
    toastErrorMock.mockClear();
  });

  it('renders the modal form', () => {
    act(() => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={generateClustersMock(1)}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    expect(screen.getByText('modal.create.title')).toBeInTheDocument();
  });

  it('validates name uniqueness', async () => {
    await act(() => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={generateClustersMock(1)}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.create.form.name.label'),
      {
        target: { value: 'project-1' },
      },
    );
    const actionButton = screen.getByText('modal.create.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(
        screen.queryByText('modal.create.form.name.validation.unique'),
      ).toBeInTheDocument();
    });
  });

  it('validates name length', async () => {
    await act(() => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={generateClustersMock(1)}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.create.form.name.label'),
      {
        target: { value: 'a ' },
      },
    );

    const actionButton = screen.getByText('modal.create.actions.confirm');
    fireEvent.click(actionButton);

    expect(
      await screen.findByText('modal.create.form.name.validation.length'),
    ).toBeInTheDocument();
  });

  it('validates name format', async () => {
    await act(() => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={generateClustersMock(1)}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.create.form.name.label'),
      {
        target: { value: 'Project-001' },
      },
    );

    const actionButton = screen.getByText('modal.create.actions.confirm');
    fireEvent.click(actionButton);

    expect(
      await screen.findByText('modal.create.form.name.validation.format'),
    ).toBeInTheDocument();
  });

  it('validates name length invalid with more than 41', async () => {
    await act(() => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={generateClustersMock(1)}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    const nameInput = screen.getByLabelText(
      'modal.create.form.name.label',
    ) as HTMLInputElement;

    await fireEvent.change(nameInput, {
      target: {
        value: '01234567890123456789012345678901234567890',
      },
    });
    const user = userEvent.setup();
    await user.type(nameInput, '89abcde');
    expect(nameInput.value.length).toBe(41);
  });

  it('validates name length valid with 41 chars', async () => {
    await act(() => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={generateClustersMock(1)}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.create.form.name.label'),
      {
        target: {
          value: '01234567890123456789012345678901234567890',
        },
      },
    );

    const actionButton = screen.getByText('modal.create.actions.confirm');
    fireEvent.click(actionButton);

    expect(
      await screen.queryByText('modal.create.form.name.validation.length'),
    ).not.toBeInTheDocument();
  });

  it('validates description length', async () => {
    await act(() => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={generateClustersMock(1)}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.create.form.description.label'),
      {
        target: { value: 'a ' },
      },
    );

    const actionButton = screen.getByText('modal.create.actions.confirm');
    await fireEvent.click(actionButton);

    expect(
      await screen.findByText(
        'modal.create.form.description.validation.length',
      ),
    ).toBeInTheDocument();
  });

  it('allows selection only of healthy clusters', async () => {
    const clusters = generateClustersMock(3);
    clusters[1].status = ClusterStatus.UNHEALTHY;
    clusters[2].status = ClusterStatus.VERIFYING;

    await act(() => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={clusters}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    const clusterSelect = screen.getByTestId('cluster-select');
    fireEvent.click(clusterSelect);

    expect(screen.queryByTestId(clusters[0].id)).toBeInTheDocument();
    expect(screen.queryByTestId(clusters[0].id)).not.toHaveAttribute(
      'data-disabled',
      'true',
    );
    expect(screen.queryByTestId(clusters[1].id)).toBeInTheDocument();
    expect(screen.queryByTestId(clusters[1].id)).toHaveAttribute(
      'data-disabled',
      'true',
    );
    expect(screen.queryByTestId(clusters[2].id)).not.toBeInTheDocument();
  });

  it('detects max projects in cluster', async () => {
    (createProject as Mock).mockResolvedValueOnce({ id: 'newProjectId' }); // Mock successful creation
    const clusters = generateClustersMock(1);
    await act(async () => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={createProjects(999)}
          clusters={clusters}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.create.form.name.label'),
      {
        target: { value: 'new-project' },
      },
    );
    await fireEvent.change(
      screen.getByLabelText('modal.create.form.description.label'),
      {
        target: { value: 'Description ' },
      },
    );

    const clusterSelect = screen.getByTestId('cluster-select');
    fireEvent.click(clusterSelect);
    const clusterOption = screen.getByTestId(clusters[0].id);
    fireEvent.click(clusterOption);

    const actionButton = screen.getByText('modal.create.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          'modal.create.form.cluster.validation.exceedProjectsCount',
        ),
      );
    });
  });

  it('calls createProject on form success', async () => {
    (createProject as Mock).mockResolvedValueOnce({ id: 'newProjectId' }); // Mock successful creation
    const clusters = generateClustersMock(1);

    await act(async () => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={clusters}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.create.form.name.label'),
      {
        target: { value: 'new-project' },
      },
    );
    await fireEvent.change(
      screen.getByLabelText('modal.create.form.description.label'),
      {
        target: { value: 'Description ' },
      },
    );

    const clusterSelect = screen.getByTestId('cluster-select');
    fireEvent.click(clusterSelect);
    const clusterOption = screen.getByTestId(clusters[0].id);
    fireEvent.click(clusterOption);

    const actionButton = screen.getByText('modal.create.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(createProject).toHaveBeenCalledWith({
        name: 'new-project',
        description: 'Description',
        cluster_id: 'cluster-1',
        quota: {
          cpu_milli_cores: 0,
          memory_bytes: 0,
          ephemeral_storage_bytes: 0,
          gpu_count: 0,
        },
      });
      expect(toastSuccessMock).toBeCalledWith(
        'modal.create.notification.success',
      );
      expect(onProjectCreate).toHaveBeenCalledWith('newProjectId');
    });
  });

  it('calls createProject on form error', async () => {
    const clusters = generateClustersMock(1);

    const mockError = new APIRequestError('test error', 400);
    (createProject as Mock).mockRejectedValueOnce(mockError);
    await act(async () => {
      render(
        <CreateProjectModal
          isOpen={true}
          onOpenChange={onOpenChange}
          projects={projects}
          clusters={clusters}
          onProjectCreate={onProjectCreate}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.create.form.name.label'),
      {
        target: { value: 'new-project' },
      },
    );
    await fireEvent.change(
      screen.getByLabelText('modal.create.form.description.label'),
      {
        target: { value: 'Description ' },
      },
    );
    const clusterSelect = screen.getByTestId('cluster-select');
    fireEvent.click(clusterSelect);
    const clusterOption = screen.getByTestId(clusters[0].id);
    fireEvent.click(clusterOption);

    const actionButton = screen.getByText('modal.create.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(createProject).toHaveBeenCalledWith({
        name: 'new-project',
        description: 'Description',
        cluster_id: 'cluster-1',
        quota: {
          cpu_milli_cores: 0,
          ephemeral_storage_bytes: 0,
          gpu_count: 0,
          memory_bytes: 0,
        },
      });
      expect(toastErrorMock).toBeCalledWith(
        'modal.create.notification.error',
        mockError,
      );
    });
  });
});
