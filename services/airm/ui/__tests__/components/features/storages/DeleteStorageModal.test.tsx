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
  generateMockProjectStorages,
  generateMockStorages,
} from '@/__mocks__/utils/storages-mock';

import { DeleteStorageModal } from '@/components/features/storages';

import wrapper from '@/__tests__/ProviderWrapper';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({ toast: mockToast }),
}));

const mockDeleteStorage = vi.fn();
const mockDeleteProjectStorages = vi.fn();
vi.mock('@/services/app/storages', () => ({
  deleteStorage: (...args: any[]) => mockDeleteStorage(...args),
  deleteProjectStorage: (...args: any[]) => mockDeleteProjectStorages(...args),
}));

describe('DeleteStorageModal', () => {
  const storage = generateMockStorages(1)[0];

  const setup = (
    props?: Partial<React.ComponentProps<typeof DeleteStorageModal>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <DeleteStorageModal
          isOpen={true}
          onOpenChange={onOpenChange}
          storage={storage}
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

  it('renders ConfirmationModal with correct props', () => {
    setup();
    expect(screen.getByText('form.delete.title')).toBeInTheDocument();
    expect(
      screen.getByText('form.delete.description', { exact: false }),
    ).toBeInTheDocument();
    expect(screen.getByText('actions.close.title')).toBeInTheDocument();
    expect(
      screen.getByText('form.delete.actions.remove.label'),
    ).toBeInTheDocument();
  });

  it('calls deleteStorage and shows success toast on confirm if not in project', async () => {
    mockDeleteStorage.mockResolvedValueOnce({});
    const { onOpenChange } = setup();

    fireEvent.click(screen.getByText('form.delete.actions.remove.label'));

    await waitFor(() => {
      expect(mockDeleteStorage).toHaveBeenCalledWith('storage-0');
      expect(mockToast.success).toHaveBeenCalledWith(
        'form.delete.notification.success',
      );
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('shows error toast on deleteStorage error if not in project', async () => {
    const error = new Error('fail');
    mockDeleteStorage.mockRejectedValueOnce(error);
    setup();

    fireEvent.click(screen.getByText('form.delete.actions.remove.label'));

    await waitFor(() => {
      expect(mockDeleteStorage).toHaveBeenCalledWith('storage-0');
      expect(mockToast.error).toHaveBeenCalledWith(
        'form.delete.notification.error',
        error,
      );
    });
  });

  it('calls assignStorage and shows success toast on confirm if inProject', async () => {
    mockDeleteProjectStorages.mockResolvedValueOnce({});

    const mockStorage = generateMockStorages(1)[0];
    mockStorage.projectStorages = generateMockProjectStorages(1);
    setup({ projectId: 'project-1', storage: mockStorage });

    await fireEvent.click(
      screen.getByRole('button', {
        name: 'form.deleteProjectStorage.actions.remove.label',
      }),
    );

    await waitFor(() => {
      expect(mockDeleteStorage).not.toHaveBeenCalled();
      expect(mockDeleteProjectStorages).toHaveBeenCalledWith(
        'project-1',
        'storage-0',
      );
      expect(mockToast.success).toHaveBeenCalledWith(
        'form.deleteProjectStorage.notification.success',
      );
    });
  });

  it('calls assignStorage and shows error toast on confirm if inProject', async () => {
    const error = new Error('fail');
    mockDeleteProjectStorages.mockRejectedValueOnce(error);

    const mockStorage = generateMockStorages(1)[0];
    mockStorage.projectStorages = generateMockProjectStorages(1);
    setup({ projectId: 'project-1', storage: mockStorage });

    fireEvent.click(
      screen.getByText('form.deleteProjectStorage.actions.remove.label'),
    );

    await waitFor(() => {
      expect(mockDeleteProjectStorages).toHaveBeenCalledWith(
        'project-1',
        'storage-0',
      );
      expect(mockToast.error).toHaveBeenCalledWith(
        'form.deleteProjectStorage.notification.error',
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
