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
  generateMockProjectSecretsWithParentSecret,
  generateMockSecrets,
} from '../../../../__mocks__/utils/secrets-mock';

import { ProjectStatus } from '@/types/enums/projects';
import { ProjectSecretStatus } from '@/types/enums/secrets';
import { ProjectWithMembers } from '@/types/projects';

import { ProjectSecrets } from '@/components/features/projects';

import wrapper from '@/__tests__/ProviderWrapper';

const mockFetchProjectSecrets = vi.fn();
vi.mock('@/services/app/secrets', () => ({
  fetchProjectSecrets: (...args: any[]) => mockFetchProjectSecrets(...args),
}));

describe('ProjectSecrets', () => {
  const secrets = generateMockSecrets(1);
  const baseProject = generateMockProjects(1)[0];
  const project: ProjectWithMembers = {
    ...baseProject,
    users: [],
    invitedUsers: [],
  };

  const projectSecrets = generateMockProjectSecretsWithParentSecret(1);

  const setup = (
    props?: Partial<React.ComponentProps<typeof ProjectSecrets>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <ProjectSecrets
          secrets={secrets}
          project={project}
          projectSecrets={projectSecrets}
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
      screen.getByText('list.headers.updatedAt.title'),
    ).toBeInTheDocument();

    expect(screen.getByText('list.filter.type.label')).toBeInTheDocument();
    expect(
      screen.queryByText('list.filter.scope.label'),
    ).not.toBeInTheDocument();
    expect(mockFetchProjectSecrets).toHaveBeenCalled();

    expect(
      screen.getByText('actions.addProjectSecret.label'),
    ).toBeInTheDocument();
  });

  it('render with disabled button if project is not ready', () => {
    setup({ project: { ...project, status: ProjectStatus.PENDING } });
    expect(
      screen.getByRole('button', { name: 'actions.addProjectSecret.label' }),
    ).toBeDisabled();
  });

  it('render not add button not disabled if project is ready', () => {
    setup({ project: { ...project, status: ProjectStatus.READY } });
    expect(
      screen.getByRole('button', { name: 'actions.addProjectSecret.label' }),
    ).not.toBeDisabled();
  });

  it('render delete row action to be not disabled when in synced state', () => {
    const mockSecrets = generateMockSecrets(1);
    const mockProjectId = 'mock-project-id';
    const mockProject = {
      ...project,
      status: ProjectStatus.READY,
      id: mockProjectId,
    };
    const mockProjectSecrets = generateMockProjectSecretsWithParentSecret(
      1,
      mockProjectId,
    );

    mockProjectSecrets[0].status = ProjectSecretStatus.SYNCED;
    mockSecrets[0].projectSecrets = mockProjectSecrets;

    setup({
      project: mockProject,
      secrets: mockSecrets,
      projectSecrets: mockProjectSecrets,
    });
    const actionButton = screen.getByRole('button', {
      name: 'list.actions.label',
    });
    expect(actionButton).toBeInTheDocument();

    fireEvent.click(actionButton);

    const deleteAction = screen.getByText(
      'list.actions.delete.projectSecret.label',
    );
    expect(deleteAction).toBeInTheDocument();
    expect(deleteAction.parentNode).not.toHaveAttribute('data-disabled');
  });

  it('render delete row action to be disabled when in deleting state', () => {
    const mockSecrets = generateMockSecrets(1);
    const mockProjectId = 'mock-project-id';
    const mockProject = {
      ...project,
      status: ProjectStatus.READY,
      id: mockProjectId,
    };
    const mockProjectSecrets = generateMockProjectSecretsWithParentSecret(
      1,
      mockProjectId,
    );

    mockProjectSecrets[0].status = ProjectSecretStatus.DELETING;
    mockSecrets[0].projectSecrets = mockProjectSecrets;

    setup({
      project: mockProject,
      secrets: mockSecrets,
      projectSecrets: mockProjectSecrets,
    });
    const actionButton = screen.getByRole('button', {
      name: 'list.actions.label',
    });
    expect(actionButton).toBeInTheDocument();

    fireEvent.click(actionButton);

    const deleteAction = screen.getByText(
      'list.actions.delete.projectSecret.label',
    );
    expect(deleteAction).toBeInTheDocument();
    expect(deleteAction.parentNode).toHaveAttribute('data-disabled', 'true');
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

    const deleteAction = screen.getByText(
      'list.actions.delete.projectSecret.label',
    );
    expect(deleteAction).toBeInTheDocument();
    act(() => {
      fireEvent.click(deleteAction);
    });

    expect(
      screen.getByText('form.deleteProjectSecret.title'),
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
