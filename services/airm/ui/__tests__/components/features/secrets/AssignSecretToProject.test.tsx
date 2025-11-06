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
import { AssignSecretToProject } from '@/components/features/secrets';
import {
  SecretScope,
  SecretUseCase,
  SecretStatus,
} from '@/types/enums/secrets';
import { Project } from '@/types/projects';
import { Secret } from '@/types/secrets';
import {
  generateMockProjectSecretsWithParentSecret,
  generateMockSecrets,
} from '@/__mocks__/utils/secrets-mock';
import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';
import { assignSecretToProject } from '@/services/app/secrets';
import { displayTimestamp } from '@/utils/app/strings';

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

vi.mock('@/services/app/secrets', () => ({
  assignSecretToProject: vi.fn(),
}));

describe('AssignSecretToProject', () => {
  const mockProject: Project = {
    id: 'project-1',
    name: 'Test Project',
  } as Project;

  const mockSecrets: Secret[] = generateMockSecrets(2);
  mockSecrets[0].projectSecrets = [];
  mockSecrets[0].status = SecretStatus.SYNCED;
  mockSecrets[1].projectSecrets = generateMockProjectSecretsWithParentSecret(
    1,
    mockProject.id,
  );
  mockSecrets[1].status = SecretStatus.SYNCED;

  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (isOpen = true, availableSecrets: Secret[] = []) => {
    return render(
      <AssignSecretToProject
        isOpen={isOpen}
        project={mockProject}
        onClose={mockOnClose}
        availableSecrets={availableSecrets}
      />,
      { wrapper },
    );
  };

  it('should not render when isOpen is false', () => {
    act(() => {
      renderComponent(false);
    });
    expect(
      screen.queryByText('form.assignSecretToProject.title'),
    ).not.toBeInTheDocument();
  });

  it('should render the drawer form when isOpen is true', () => {
    act(() => {
      renderComponent(true);
    });
    expect(
      screen.getByText('form.assignSecretToProject.title'),
    ).toBeInTheDocument();
  });

  it('should render blank secret details section on initial render', () => {
    act(() => {
      renderComponent(true);
    });

    expect(
      screen.getByText('form.assignSecretToProject.details.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('form.assignSecretToProject.details.type'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('form.assignSecretToProject.details.useCase'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('form.assignSecretToProject.details.updatedAt'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('form.assignSecretToProject.details.assignTo'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('form.assignSecretToProject.details.status'),
    ).toBeInTheDocument();
  });

  it('should render detail when secret is selected', async () => {
    const mockSecrets = generateMockSecrets(1);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.SYNCED;
    mockSecrets[0].useCase = SecretUseCase.HUGGING_FACE;

    mockSecrets[0].projectSecrets = generateMockProjectSecretsWithParentSecret(
      2,
      '2',
    );

    act(() => {
      renderComponent(true, mockSecrets);
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignSecretToProject.title'),
      ).toBeInTheDocument();
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignSecretToProject.field.secretId.placeholder form.assignSecretToProject.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOption = screen.getByRole('option', { name: 'My Secret 1' });

    await fireEvent.click(secretOption);

    expect(
      screen.getByText(`useCase.${mockSecrets[0].useCase}`),
    ).toBeInTheDocument();
    expect(screen.getByText('2 projects')).toBeInTheDocument();
    expect(
      screen.getByText(displayTimestamp(new Date(mockSecrets[0].updatedAt))),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(SecretStatus.SYNCED)).toBeInTheDocument();
  });

  it('should render detail when secret use case as Generic if type is not specified', async () => {
    const mockSecrets = generateMockSecrets(1);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.SYNCED;
    mockSecrets[0].useCase = undefined;

    mockSecrets[0].projectSecrets = generateMockProjectSecretsWithParentSecret(
      2,
      '2',
    );

    act(() => {
      renderComponent(true, mockSecrets);
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignSecretToProject.title'),
      ).toBeInTheDocument();
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignSecretToProject.field.secretId.placeholder form.assignSecretToProject.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOption = screen.getByRole('option', { name: 'My Secret 1' });

    await fireEvent.click(secretOption);

    expect(screen.getByText('2 projects')).toBeInTheDocument();
    expect(
      screen.getByText(displayTimestamp(new Date(mockSecrets[0].updatedAt))),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(SecretStatus.SYNCED)).toBeInTheDocument();
  });

  it('should call assign with correct payload', async () => {
    const mockSecrets = generateMockSecrets(1);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.UNASSIGNED;
    mockSecrets[0].projectSecrets = [];

    act(() => {
      renderComponent(true, mockSecrets);
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignSecretToProject.title'),
      ).toBeInTheDocument();
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignSecretToProject.field.secretId.placeholder form.assignSecretToProject.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOption = screen.getByRole('option', { name: 'My Secret 1' });

    await fireEvent.click(secretOption);

    const confirmButton = screen.getByRole('button', {
      name: 'form.assignSecretToProject.action.save',
    });

    await fireEvent.click(confirmButton);
    expect(screen.getByLabelText(SecretStatus.UNASSIGNED)).toBeInTheDocument();

    await waitFor(() => {
      expect(assignSecretToProject).toHaveBeenCalledWith(
        mockProject.id,
        mockSecrets[0].id,
      );
    });
  });

  it('test successful notification', async () => {
    const mockSecrets = generateMockSecrets(1);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.UNASSIGNED;
    mockSecrets[0].useCase = SecretUseCase.HUGGING_FACE;
    mockSecrets[0].projectSecrets = [];

    (assignSecretToProject as Mock).mockResolvedValueOnce({});

    act(() => {
      renderComponent(true, mockSecrets);
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignSecretToProject.title'),
      ).toBeInTheDocument();
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignSecretToProject.field.secretId.placeholder form.assignSecretToProject.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOption = screen.getByRole('option', { name: 'My Secret 1' });

    await fireEvent.click(secretOption);

    const confirmButton = screen.getByRole('button', {
      name: 'form.assignSecretToProject.action.save',
    });

    await fireEvent.click(confirmButton);
    expect(screen.getByLabelText(SecretStatus.UNASSIGNED)).toBeInTheDocument();

    await waitFor(() => {
      expect(assignSecretToProject).toHaveBeenCalledWith(
        mockProject.id,
        mockSecrets[0].id,
      );
    });

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith(
        'form.assignSecretToProject.notification.success',
      );
    });
  });

  it('test error notification', async () => {
    const mockSecrets = generateMockSecrets(1);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.UNASSIGNED;
    mockSecrets[0].useCase = SecretUseCase.HUGGING_FACE;
    mockSecrets[0].projectSecrets = [];

    const mockError = new Error('Test error');
    (assignSecretToProject as Mock).mockRejectedValueOnce(mockError);

    act(() => {
      renderComponent(true, mockSecrets);
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignSecretToProject.title'),
      ).toBeInTheDocument();
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignSecretToProject.field.secretId.placeholder form.assignSecretToProject.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOption = screen.getByRole('option', { name: 'My Secret 1' });

    await fireEvent.click(secretOption);

    const confirmButton = screen.getByRole('button', {
      name: 'form.assignSecretToProject.action.save',
    });

    await fireEvent.click(confirmButton);
    expect(screen.getByLabelText(SecretStatus.UNASSIGNED)).toBeInTheDocument();

    await waitFor(() => {
      expect(assignSecretToProject).toHaveBeenCalledWith(
        mockProject.id,
        mockSecrets[0].id,
      );
    });

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'form.assignSecretToProject.notification.error',
        mockError,
      );
    });
  });
});
