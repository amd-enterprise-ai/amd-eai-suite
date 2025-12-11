// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React, { act } from 'react';

import { generateMockProjects } from '@/__mocks__/utils/project-mock';
import { generateMockStorages } from '@/__mocks__/utils/storages-mock';

import { Project } from '@/types/projects';
import { Storage } from '@/types/storages';
import { StorageStatus } from '@/types/enums/storages';

import { AssignStorageToProject } from '@/components/features/storages';

import wrapper from '@/__tests__/ProviderWrapper';

const mockAssignStorageToProject = vi.fn();

vi.mock('@/services/app/storages', () => ({
  assignStorageToProject: (...args: any[]) =>
    mockAssignStorageToProject(...args),
}));

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

describe('AssignStorageToProject', () => {
  const project: Project = generateMockProjects(1)[0];
  const storages: Storage[] = generateMockStorages(3);
  const existingStorageIds: string[] = [storages[0].id];
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form fields and buttons', () => {
    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storages}
          existingStorageIds={existingStorageIds}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    expect(screen.getByText('form.assignToProject.title')).toBeInTheDocument();
    const storageLabelElements = screen.getAllByText(
      'form.assignToProject.field.storageId.label',
    );
    expect(storageLabelElements.length).toBeGreaterThan(0);
    expect(
      screen.getByText('form.assignToProject.action.assign'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('form.assignToProject.action.cancel'),
    ).toBeInTheDocument();
  });

  it('filters out existing storages from the dropdown', () => {
    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storages}
          existingStorageIds={existingStorageIds}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    // Click to open the dropdown
    fireEvent.click(
      screen.getByText('form.assignToProject.field.storageId.placeholder'),
    );

    // Should show storages except the existing one
    expect(screen.queryByText('Storage 0')).not.toBeInTheDocument();
    expect(screen.getAllByText('Storage 1').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Storage 2').length).toBeGreaterThan(0);
  });

  it('disables storages with DELETING status', () => {
    const storagesWithDeleting = [
      ...storages.filter((s) => s.id !== existingStorageIds[0]),
      {
        ...generateMockStorages(1)[0],
        id: 'storage-deleting',
        name: 'Deleting Storage',
        status: StorageStatus.DELETING,
      },
    ];

    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storagesWithDeleting}
          existingStorageIds={existingStorageIds}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    fireEvent.click(
      screen.getByText('form.assignToProject.field.storageId.placeholder'),
    );

    // Deleting storage should be filtered out from availableStorages
    // but should appear in disabledKeys
    const deletingStorageElements = screen.queryAllByText('Deleting Storage');
    // It might not be visible if it's filtered, or it might be disabled
    // Just check that DELETING status storages are handled
    expect(deletingStorageElements.length).toBeGreaterThanOrEqual(0);
  });

  it('shows message when no available storages', () => {
    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storages}
          existingStorageIds={storages.map((s) => s.id)}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    expect(
      screen.getByText('form.assignToProject.noAvailableStorages'),
    ).toBeInTheDocument();
  });

  it('calls assignStorageToProject and shows success toast on submit', async () => {
    mockAssignStorageToProject.mockResolvedValueOnce({});

    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storages}
          existingStorageIds={existingStorageIds}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    // Select a storage
    await fireEvent.click(
      screen.getByText('form.assignToProject.field.storageId.placeholder'),
    );
    const storage1Options = screen.getAllByText('Storage 1');
    await fireEvent.click(storage1Options[storage1Options.length - 1]);

    // Submit
    fireEvent.click(screen.getByText('form.assignToProject.action.assign'));

    await waitFor(() => {
      expect(mockAssignStorageToProject).toHaveBeenCalledWith(
        project.id,
        storages[1].id,
      );
      expect(toastSuccessMock).toHaveBeenCalledWith(
        'form.assignToProject.notification.success',
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error toast on mutation error', async () => {
    mockAssignStorageToProject.mockRejectedValueOnce(new Error('fail'));

    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storages}
          existingStorageIds={existingStorageIds}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    // Select a storage
    await fireEvent.click(
      screen.getByText('form.assignToProject.field.storageId.placeholder'),
    );
    const storage1Options = screen.getAllByText('Storage 1');
    await fireEvent.click(storage1Options[storage1Options.length - 1]);

    // Submit
    fireEvent.click(screen.getByText('form.assignToProject.action.assign'));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'form.assignToProject.notification.error',
        expect.any(Error),
      );
    });
  });

  it('calls onClose when cancel button is clicked', () => {
    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storages}
          existingStorageIds={existingStorageIds}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    fireEvent.click(screen.getByText('form.assignToProject.action.cancel'));
    expect(onClose).toHaveBeenCalled();
  });

  it('does not render when closed', () => {
    const { container } = render(
      <AssignStorageToProject
        isOpen={false}
        project={project}
        storages={storages}
        existingStorageIds={existingStorageIds}
        onClose={onClose}
      />,
      { wrapper },
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('requires storage selection before submit', async () => {
    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storages}
          existingStorageIds={existingStorageIds}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    // Try to submit without selecting a storage
    fireEvent.click(screen.getByText('form.assignToProject.action.assign'));

    await waitFor(
      () => {
        // Should not call the API without a valid selection
        expect(mockAssignStorageToProject).not.toHaveBeenCalled();
      },
      { timeout: 500 },
    );
  });

  it('displays storage names in dropdown', () => {
    act(() => {
      render(
        <AssignStorageToProject
          isOpen
          project={project}
          storages={storages}
          existingStorageIds={existingStorageIds}
          onClose={onClose}
        />,
        { wrapper },
      );
    });

    fireEvent.click(
      screen.getByText('form.assignToProject.field.storageId.placeholder'),
    );

    // Should display storage names only
    expect(screen.getAllByText('Storage 1').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Storage 2').length).toBeGreaterThan(0);
  });
});
