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
  generateMockProjectSecrets,
  generateMockSecrets,
} from '../../../../__mocks__/utils/secrets-mock';

import DeleteSecretModal from '@/components/features/secrets/DeleteSecretModal';

import wrapper from '@/__tests__/ProviderWrapper';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({ toast: mockToast }),
}));

const mockDeleteSecret = vi.fn();
const mockDeleteProjectSecrets = vi.fn();
vi.mock('@/services/app/secrets', () => ({
  deleteSecret: (...args: any[]) => mockDeleteSecret(...args),
  deleteProjectSecret: (...args: any[]) => mockDeleteProjectSecrets(...args),
}));

vi.mock('next-i18next', () => ({
  Trans: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTranslation: () => ({
    t: (key: string) => key, // Simple pass-through mock
  }),
}));

describe('DeleteSecretModal', () => {
  const secret = generateMockSecrets(1)[0];

  const setup = (
    props?: Partial<React.ComponentProps<typeof DeleteSecretModal>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <DeleteSecretModal
          isOpen={true}
          onOpenChange={onOpenChange}
          secret={secret}
          queryKeyToInvalidate={['secrets']}
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

  it('renders null if secret is null', () => {
    let container: HTMLElement | null = null;
    act(() => {
      const renderResult = render(
        <DeleteSecretModal
          isOpen={true}
          onOpenChange={vi.fn()}
          secret={null}
          queryKeyToInvalidate={['secrets']}
        />,
        { wrapper },
      );
      container = renderResult.container;
    });
    expect(container!.firstChild).toBeNull();
  });

  it('renders ConfirmationModal with correct props', () => {
    setup();
    expect(screen.getByText('form.delete.title')).toBeInTheDocument();
    expect(
      screen.getByText('form.delete.description', { exact: false }),
    ).toBeInTheDocument();
    expect(screen.getByText('actions.close.title')).toBeInTheDocument();
    expect(screen.getByText('actions.confirm.title')).toBeInTheDocument();
  });

  it('calls deleteSecret and shows success toast on confirm if not in project', async () => {
    mockDeleteSecret.mockResolvedValueOnce({});
    const { onOpenChange } = setup();

    fireEvent.click(screen.getByText('actions.confirm.title'));

    await waitFor(() => {
      expect(mockDeleteSecret).toHaveBeenCalledWith('secret-1');
      expect(mockToast.success).toHaveBeenCalledWith(
        'form.delete.notification.success',
      );
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('shows error toast on deleteSecret error if not in project', async () => {
    const error = new Error('fail');
    mockDeleteSecret.mockRejectedValueOnce(error);
    setup();

    fireEvent.click(screen.getByText('actions.confirm.title'));

    await waitFor(() => {
      expect(mockDeleteSecret).toHaveBeenCalledWith('secret-1');
      expect(mockToast.error).toHaveBeenCalledWith(
        'form.delete.notification.error',
        error,
      );
    });
  });

  it('calls assignSecret and shows success toast on confirm if inProject', async () => {
    mockDeleteProjectSecrets.mockResolvedValueOnce({});

    const mockSecret = generateMockSecrets(1)[0];
    mockSecret.projectSecrets = generateMockProjectSecrets(1, 'project-1');
    setup({ projectId: 'project-1', secret: mockSecret });

    await fireEvent.click(screen.getByText('actions.confirm.title'));

    await waitFor(() => {
      expect(mockDeleteSecret).not.toHaveBeenCalled();
      expect(mockDeleteProjectSecrets).toHaveBeenCalledWith(
        'project-1',
        'secret-1',
      );
      expect(mockToast.success).toHaveBeenCalledWith(
        'form.deleteProjectSecret.notification.success',
      );
    });
  });

  it('calls assignSecret and shows error toast on confirm if inProject', async () => {
    const error = new Error('fail');
    mockDeleteProjectSecrets.mockRejectedValueOnce(error);

    const mockSecret = generateMockSecrets(1)[0];
    mockSecret.projectSecrets = generateMockProjectSecrets(1, 'project-1');
    setup({ projectId: 'project-1', secret: mockSecret });

    fireEvent.click(screen.getByText('actions.confirm.title'));

    await waitFor(() => {
      expect(mockDeleteProjectSecrets).toHaveBeenCalledWith(
        'project-1',
        'secret-1',
      );
      expect(mockToast.error).toHaveBeenCalledWith(
        'form.deleteProjectSecret.notification.error',
        error,
      );
    });
  });

  it('calls onOpenChange(false) when closed', () => {
    const { onOpenChange } = setup();
    fireEvent.click(screen.getByText('actions.close.title'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
