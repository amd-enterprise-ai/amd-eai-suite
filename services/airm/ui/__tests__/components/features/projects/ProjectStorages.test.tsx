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

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';
import {
  generateMockProjectSecrets,
  generateMockSecrets,
} from '../../../../__mocks__/utils/secrets-mock';
import {
  generateMockProjectStoragesWithParentStorage,
  generateMockStorages,
} from '@/__mocks__/utils/storages-mock';

import { ProjectStatus } from '@/types/enums/projects';
import { ProjectSecretStatus } from '@/types/enums/secrets';
import { ProjectStorageStatus } from '@/types/enums/storages';
import { ProjectWithMembers } from '@/types/projects';

import { ProjectStorages } from '@/components/features/projects';

import wrapper from '@/__tests__/ProviderWrapper';

const mockFetchProjectSecrets = vi.fn();
const mockFetchProjectStorages = vi.fn();

vi.mock('@/services/app/secrets', () => ({
  fetchProjectSecrets: (...args: any[]) => mockFetchProjectSecrets(...args),
}));

vi.mock('@/services/app/storages', () => ({
  fetchProjectStorages: (...args: any[]) => mockFetchProjectStorages(...args),
}));

describe('ProjectStorages', () => {
  const secrets = generateMockSecrets(1);
  const projectStorages = generateMockProjectStoragesWithParentStorage(1);
  const storages = generateMockStorages(1);

  const baseProject = generateMockProjects(1)[0];
  const project: ProjectWithMembers = {
    ...baseProject,
    users: [],
    invitedUsers: [],
  };

  const setup = (
    props?: Partial<React.ComponentProps<typeof ProjectStorages>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <ProjectStorages
          storages={storages}
          projectStorages={projectStorages}
          secrets={secrets}
          project={project}
          {...props}
        />,
        { wrapper },
      );
    });
    return { onOpenChange };
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('render without crashing', () => {
    setup();
    expect(screen.getByText('list.headers.name.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.type.title')).toBeInTheDocument();
    expect(screen.getByText('list.headers.status.title')).toBeInTheDocument();
    expect(
      screen.getByText('list.headers.createdAt.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('list.headers.createdBy.title'),
    ).toBeInTheDocument();
    expect(mockFetchProjectStorages).toHaveBeenCalled();

    expect(
      screen.getByText('actions.addProjectStorage.label'),
    ).toBeInTheDocument();
  });

  it('render with disabled button if project is not ready', () => {
    setup({ project: { ...project, status: ProjectStatus.PENDING } });
    expect(
      screen.getByRole('button', { name: 'actions.addProjectStorage.label' }),
    ).toBeDisabled();
  });

  it('render not add button not disabled if project is ready', () => {
    setup({ project: { ...project, status: ProjectStatus.READY } });
    expect(
      screen.getByRole('button', { name: 'actions.addProjectStorage.label' }),
    ).not.toBeDisabled();
  });

  it('render delete row action to be not disabled when in synced state', () => {
    const mockStorages = generateMockStorages(1);
    const mockProjectId = 'mock-project-id';
    const mockProject = {
      ...project,
      status: ProjectStatus.READY,
      id: mockProjectId,
    };
    const mockProjectStorages = generateMockProjectStoragesWithParentStorage(
      1,
      mockProjectId,
    );

    mockProjectStorages[0].status = ProjectStorageStatus.SYNCED;
    mockStorages[0].projectStorages = mockProjectStorages;

    setup({
      project: mockProject,
      storages: mockStorages,
      projectStorages: mockProjectStorages,
    });
    const actionButton = screen.getByRole('button', {
      name: 'list.actions.label',
    });
    expect(actionButton).toBeInTheDocument();

    fireEvent.click(actionButton);

    const deleteAction = screen.getByRole('menuitem', {
      name: 'list.actions.deleteFromProject.label',
    });
    expect(deleteAction).toBeInTheDocument();
    expect(deleteAction).not.toHaveAttribute('data-disabled');
  });

  it('render delete row action to be disabled when in deleting state', () => {
    const mockStorages = generateMockStorages(1);
    const mockProjectId = 'mock-project-id';
    const mockProject = {
      ...project,
      status: ProjectStatus.READY,
      id: mockProjectId,
    };
    const mockProjectStorages = generateMockProjectStoragesWithParentStorage(
      1,
      mockProjectId,
    );

    mockProjectStorages[0].status = ProjectStorageStatus.DELETING;
    mockStorages[0].projectStorages = mockProjectStorages;

    setup({
      project: mockProject,
      storages: mockStorages,
      projectStorages: mockProjectStorages,
    });
    const actionButton = screen.getByRole('button', {
      name: 'list.actions.label',
    });
    expect(actionButton).toBeInTheDocument();

    fireEvent.click(actionButton);

    const deleteAction = screen.getByRole('menuitem', {
      name: 'list.actions.deleteFromProject.label',
    });
    expect(deleteAction).toBeInTheDocument();
    expect(deleteAction).toHaveAttribute('data-disabled', 'true');
  });

  it('delete button shows secrets delete confirm modal ', () => {
    const mockSecrets = generateMockSecrets(1);
    const mockProjectId = 'mock-project-id';
    const mockProjectSecrets = generateMockProjectSecrets(1, mockProjectId);
    mockProjectSecrets[0].status = ProjectSecretStatus.PENDING;
    mockSecrets[0].projectSecrets = mockProjectSecrets;
    const mockProject = {
      ...project,
      status: ProjectStatus.READY,
      id: mockProjectId,
    };

    setup({
      project: mockProject,
      secrets: mockSecrets,
    });
    const actionButton = screen.getByRole('button', {
      name: 'list.actions.label',
    });
    expect(actionButton).toBeInTheDocument();

    fireEvent.click(actionButton);

    const deleteAction = screen.getByRole('menuitem', {
      name: 'list.actions.deleteFromProject.label',
    });
    expect(deleteAction).toBeInTheDocument();
    act(() => {
      fireEvent.click(deleteAction);
    });

    expect(
      screen.getByText('form.deleteProjectStorage.title'),
    ).toBeInTheDocument();
  });

  it('filter will return correct secrets', async () => {
    const mockSecrets = generateMockSecrets(2);
    const mockProjectId = 'mock-project-id';
    const mockProjectSecrets = generateMockProjectSecrets(1, mockProjectId);
    mockProjectSecrets[0].status = ProjectSecretStatus.PENDING;
    mockSecrets[0].projectSecrets = mockProjectSecrets;
    const mockProject = {
      ...project,
      status: ProjectStatus.READY,
      id: mockProjectId,
    };

    await setup({
      project: mockProject,
      secrets: mockSecrets,
    });
    const filterInput = screen.getByLabelText('list.filter.search.label');
    expect(filterInput).toBeInTheDocument();

    await act(() => {
      fireEvent.change(filterInput, { target: { value: 'none' } });
    });

    await waitFor(() => {
      expect(screen.getByText('list.empty.description')).toBeInTheDocument();
    });
  });
});
