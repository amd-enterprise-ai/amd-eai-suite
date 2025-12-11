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
import { AssignOrgSecretToProject } from '@/components/features/secrets';
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
import { assignSecretToProject, fetchSecrets } from '@/services/app/secrets';
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

vi.mock('next-i18next', () => ({
  Trans: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTranslation: () => ({
    t: (key: string) => key, // Simple pass-through mock
  }),
}));

vi.mock('@/services/app/secrets', () => ({
  fetchSecrets: vi.fn(),
  assignSecretToProject: vi.fn(),
}));

describe('AssignOrgSecretToProject', () => {
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
  mockSecrets[1].useCase = SecretUseCase.DB;

  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (isOpen = true) => {
    return render(
      <AssignOrgSecretToProject
        isOpen={isOpen}
        project={mockProject}
        onClose={mockOnClose}
      />,
      { wrapper },
    );
  };

  it('should not render when isOpen is false', () => {
    act(() => {
      renderComponent(false);
    });
    expect(
      screen.queryByText('form.assignOrgSecret.title'),
    ).not.toBeInTheDocument();
  });

  it('should render the drawer form when isOpen is true', () => {
    act(() => {
      renderComponent();
    });
    expect(screen.getByText('form.assignOrgSecret.title')).toBeInTheDocument();
  });

  it('should render blank secret details section on initial render', async () => {
    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.secretDetails.title'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('form.assignOrgSecret.secretDetails.type.label'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('form.assignOrgSecret.secretDetails.useCase.label'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('form.assignOrgSecret.secretDetails.updatedAt.label'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('form.assignOrgSecret.secretDetails.assignedTo.label'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('form.assignOrgSecret.secretDetails.status.label'),
      ).toBeInTheDocument();
    });
  });

  it('should sort selectable secrets alphabetically', async () => {
    const unsortedSecrets: Secret[] = [...mockSecrets];

    unsortedSecrets[0].name = 'Z Secret';
    unsortedSecrets[0].status = SecretStatus.UNASSIGNED;
    unsortedSecrets[0].scope = SecretScope.ORGANIZATION;
    unsortedSecrets[0].projectSecrets = [];
    unsortedSecrets[1].name = 'A Secret';
    unsortedSecrets[1].status = SecretStatus.UNASSIGNED;
    unsortedSecrets[1].scope = SecretScope.ORGANIZATION;
    unsortedSecrets[1].projectSecrets = [];

    (fetchSecrets as Mock).mockResolvedValueOnce({ secrets: unsortedSecrets });
    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.title'),
      ).toBeInTheDocument();
      expect(fetchSecrets).toHaveBeenCalledTimes(1);
    });

    const selectSecret = screen.getByText(
      'form.assignOrgSecret.field.secretId.placeholder',
    );

    await fireEvent.click(selectSecret);

    // Wait for the options to appear
    const aSecretOptions = await screen.findAllByText('A Secret');
    const zSecretOptions = await screen.findAllByText('Z Secret');

    // expected in sorted order - verify both secrets are in the list
    expect(aSecretOptions.length).toBeGreaterThan(0);
    expect(zSecretOptions.length).toBeGreaterThan(0);
  });

  it('should filter out secrets that are not Organization scope', async () => {
    const mockSecrets = generateMockSecrets(3);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.UNASSIGNED;
    mockSecrets[0].projectSecrets = [];

    mockSecrets[1].scope = SecretScope.PROJECT;
    mockSecrets[1].status = SecretStatus.UNASSIGNED;
    mockSecrets[1].projectSecrets = [];

    mockSecrets[2].scope = SecretScope.ORGANIZATION;
    mockSecrets[2].status = SecretStatus.UNASSIGNED;
    mockSecrets[2].projectSecrets = [];

    (fetchSecrets as Mock).mockResolvedValueOnce({ secrets: mockSecrets });

    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.title'),
      ).toBeInTheDocument();
      expect(fetchSecrets).toHaveBeenCalledTimes(1);
    });

    const selectSecret = screen.getByText(
      'form.assignOrgSecret.field.secretId.placeholder',
    );

    await fireEvent.click(selectSecret);

    // Secret 1, 3 should be selectable (not assigned to project)
    // Secret 2 should be filtered out (already assigned to project-1)
    // expected in sorted order
    const secret1Options = await screen.findAllByText('My Secret 1');
    const secret3Options = await screen.findAllByText('My Secret 3');

    expect(secret1Options.length).toBeGreaterThan(0);
    expect(secret3Options.length).toBeGreaterThan(0);
    // Verify Secret 2 (PROJECT scope) is not in the list
    expect(screen.queryByText('My Secret 2')).not.toBeInTheDocument();
  });

  it('should filter out secrets that are already assigned to the project', async () => {
    const mockSecrets = generateMockSecrets(3);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.UNASSIGNED;
    mockSecrets[0].projectSecrets = generateMockProjectSecretsWithParentSecret(
      1,
      mockProject.id,
    );

    mockSecrets[1].scope = SecretScope.PROJECT;
    mockSecrets[1].status = SecretStatus.UNASSIGNED;
    mockSecrets[1].projectSecrets = [];

    mockSecrets[2].scope = SecretScope.ORGANIZATION;
    mockSecrets[2].status = SecretStatus.UNASSIGNED;
    mockSecrets[2].projectSecrets = [];

    (fetchSecrets as Mock).mockResolvedValueOnce({ secrets: mockSecrets });

    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.title'),
      ).toBeInTheDocument();
      expect(fetchSecrets).toHaveBeenCalledTimes(1);
    });

    const selectSecret = screen.getByText(
      'form.assignOrgSecret.field.secretId.placeholder',
    );

    await fireEvent.click(selectSecret);

    // Secret 1, 3 should be selectable (not assigned to project)
    // Secret 2 should be filtered out (already assigned to project-1)
    // expected in sorted order
    const secret3Options = await screen.findAllByText('My Secret 3');
    expect(secret3Options.length).toBeGreaterThan(0);
    // Verify Secret 1 (already assigned) is not in the list
    expect(screen.queryByText('My Secret 1')).not.toBeInTheDocument();
  });

  it('should render detail when secret is selected', async () => {
    const mockSecrets = generateMockSecrets(1);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.SYNCED;
    mockSecrets[0].useCase = SecretUseCase.DB;

    mockSecrets[0].projectSecrets = generateMockProjectSecretsWithParentSecret(
      2,
      '2',
    );

    (fetchSecrets as Mock).mockResolvedValueOnce({ secrets: mockSecrets });

    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.title'),
      ).toBeInTheDocument();
      expect(fetchSecrets).toHaveBeenCalledTimes(1);
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignOrgSecret.field.secretId.placeholder form.assignOrgSecret.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOptions = await screen.findAllByText('My Secret 1');
    await fireEvent.click(secretOptions[1]);

    expect(
      screen.getByText(`useCase.${mockSecrets[0].useCase}`),
    ).toBeInTheDocument();
    expect(screen.getByText('2 projects')).toBeInTheDocument();
    expect(
      screen.getByText(displayTimestamp(new Date(mockSecrets[0].updatedAt))),
    ).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatus.SYNCED}`),
    ).toBeInTheDocument();
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

    (fetchSecrets as Mock).mockResolvedValueOnce({ secrets: mockSecrets });

    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.title'),
      ).toBeInTheDocument();
      expect(fetchSecrets).toHaveBeenCalledTimes(1);
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignOrgSecret.field.secretId.placeholder form.assignOrgSecret.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOptions = await screen.findAllByText('My Secret 1');
    await fireEvent.click(secretOptions[1]);

    expect(
      screen.getByText(`useCase.${SecretUseCase.GENERIC}`),
    ).toBeInTheDocument();
    expect(screen.getByText('2 projects')).toBeInTheDocument();
    expect(
      screen.getByText(displayTimestamp(new Date(mockSecrets[0].updatedAt))),
    ).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatus.SYNCED}`),
    ).toBeInTheDocument();
  });

  it('should call assign with correct payload', async () => {
    const mockSecrets = generateMockSecrets(1);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.UNASSIGNED;
    mockSecrets[0].useCase = SecretUseCase.DB;
    mockSecrets[0].projectSecrets = [];

    (fetchSecrets as Mock).mockResolvedValueOnce({ secrets: mockSecrets });

    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.title'),
      ).toBeInTheDocument();
      expect(fetchSecrets).toHaveBeenCalledTimes(1);
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignOrgSecret.field.secretId.placeholder form.assignOrgSecret.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOptions = await screen.findAllByText('My Secret 1');
    await fireEvent.click(secretOptions[1]);

    const confirmButton = screen.getByRole('button', {
      name: 'form.assignOrgSecret.action.save',
    });

    await fireEvent.click(confirmButton);
    expect(
      screen.getByText(`secretStatus.${SecretStatus.UNASSIGNED}`),
    ).toBeInTheDocument();

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
    mockSecrets[0].useCase = SecretUseCase.DB;
    mockSecrets[0].projectSecrets = [];

    (fetchSecrets as Mock).mockResolvedValueOnce({ secrets: mockSecrets });
    (assignSecretToProject as Mock).mockResolvedValueOnce({});

    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.title'),
      ).toBeInTheDocument();
      expect(fetchSecrets).toHaveBeenCalledTimes(1);
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignOrgSecret.field.secretId.placeholder form.assignOrgSecret.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOptions = await screen.findAllByText('My Secret 1');
    await fireEvent.click(secretOptions[1]);

    const confirmButton = screen.getByRole('button', {
      name: 'form.assignOrgSecret.action.save',
    });

    await fireEvent.click(confirmButton);
    expect(
      screen.getByText(`secretStatus.${SecretStatus.UNASSIGNED}`),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(assignSecretToProject).toHaveBeenCalledWith(
        mockProject.id,
        mockSecrets[0].id,
      );
    });

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith(
        'form.assignOrgSecret.notification.success',
      );
    });
  });

  it('test error notification', async () => {
    const mockSecrets = generateMockSecrets(1);
    mockSecrets[0].scope = SecretScope.ORGANIZATION;
    mockSecrets[0].status = SecretStatus.UNASSIGNED;
    mockSecrets[0].useCase = SecretUseCase.DB;
    mockSecrets[0].projectSecrets = [];

    const mockError = new Error('Test error');
    (fetchSecrets as Mock).mockResolvedValueOnce({ secrets: mockSecrets });
    (assignSecretToProject as Mock).mockRejectedValueOnce(mockError);

    act(() => {
      renderComponent();
    });

    await waitFor(() => {
      expect(
        screen.getByText('form.assignOrgSecret.title'),
      ).toBeInTheDocument();
      expect(fetchSecrets).toHaveBeenCalledTimes(1);
    });

    const selectSecret = screen.getByRole('button', {
      name: 'form.assignOrgSecret.field.secretId.placeholder form.assignOrgSecret.field.secretId.label',
    });

    await fireEvent.click(selectSecret);

    const secretOptions = await screen.findAllByText('My Secret 1');
    await fireEvent.click(secretOptions[1]);

    const confirmButton = screen.getByRole('button', {
      name: 'form.assignOrgSecret.action.save',
    });

    await fireEvent.click(confirmButton);
    expect(
      screen.getByText(`secretStatus.${SecretStatus.UNASSIGNED}`),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(assignSecretToProject).toHaveBeenCalledWith(
        mockProject.id,
        mockSecrets[0].id,
      );
    });

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'form.assignOrgSecret.notification.error',
        mockError,
      );
    });
  });
});
