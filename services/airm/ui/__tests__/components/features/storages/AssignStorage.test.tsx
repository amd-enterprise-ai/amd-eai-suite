// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React, { act } from 'react';

import { generateMockProjects } from '@/__mocks__/utils/project-mock';
import { generateMockStorages } from '@/__mocks__/utils/storages-mock';

import { Project } from '@/types/projects';
import { Storage } from '@/types/storages';

import { AssignStorage } from '@/components/features/storages';

import wrapper from '@/__tests__/ProviderWrapper';
import { updateStorageAssignment } from '@/services/app/storages';

const mockUpdateStorageAssignment = vi.fn();

vi.mock('@/services/app/storages', () => ({
  updateStorageAssignment: (...args: any[]) =>
    mockUpdateStorageAssignment(...args),
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

describe('AssignStorage', () => {
  const projects: Project[] = [];
  const storage: Storage = generateMockStorages(1)[0];
  const selectedProjectIds: string[] = [];
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form fields and buttons', () => {
    act(() => {
      render(
        <AssignStorage
          isOpen
          storage={storage}
          projects={[]}
          selectedProjectIds={selectedProjectIds}
          onClose={onClose}
          disabledProjectIds={[]}
        />,
        { wrapper },
      );
    });

    expect(screen.getByText('form.assign.title')).toBeInTheDocument();
    const projectLabelElements = screen.getAllByText(
      'form.assign.field.projectIds.label',
    );
    expect(projectLabelElements.length).toBeGreaterThan(0);
    expect(screen.getByText('form.assign.action.save')).toBeInTheDocument();
    expect(screen.getByText('form.assign.action.cancel')).toBeInTheDocument();
  });

  it('calls updateStorageAssignment and shows success toast on submit', async () => {
    const mockProjects: Project[] = generateMockProjects(3);

    mockUpdateStorageAssignment.mockResolvedValueOnce({});
    act(() =>
      render(
        <AssignStorage
          isOpen
          storage={storage}
          projects={mockProjects}
          selectedProjectIds={selectedProjectIds}
          onClose={onClose}
          disabledProjectIds={[]}
        />,
        { wrapper },
      ),
    );

    fireEvent.click(screen.getByText('form.assign.action.save'));
    await waitFor(() => {
      expect(mockUpdateStorageAssignment).toHaveBeenCalledWith(storage.id, {
        project_ids: [],
      });
      expect(toastSuccessMock).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('calls updateStorageAssignment disabled project id', async () => {
    mockUpdateStorageAssignment.mockResolvedValueOnce({});

    const mockProjects: Project[] = generateMockProjects(1);

    await act(() =>
      render(
        <AssignStorage
          isOpen
          storage={storage}
          projects={mockProjects}
          selectedProjectIds={[]}
          disabledProjectIds={[mockProjects[0].id]}
          onClose={onClose}
        />,
        { wrapper },
      ),
    );

    await fireEvent.click(
      screen.getByText('form.assign.field.projectIds.placeholder'),
    );
    const options = await screen.findAllByText('project-1');
    await fireEvent.click(options[1]);

    await fireEvent.click(screen.getByText('form.assign.action.save'));

    await waitFor(() => {
      expect(mockUpdateStorageAssignment).toHaveBeenCalledWith(storage.id, {
        project_ids: [],
      });
      expect(toastSuccessMock).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('calls updateStorageAssignment and select multiple project to be passed in', async () => {
    mockUpdateStorageAssignment.mockResolvedValueOnce({});

    const mockProjects: Project[] = generateMockProjects(3);

    await act(() =>
      render(
        <AssignStorage
          isOpen
          storage={storage}
          projects={mockProjects}
          selectedProjectIds={[]}
          disabledProjectIds={[]}
          onClose={onClose}
        />,
        { wrapper },
      ),
    );

    await fireEvent.click(
      screen.getByText('form.assign.field.projectIds.placeholder'),
    );
    await fireEvent.click(screen.getAllByText('project-1')[1]);
    await fireEvent.click(screen.getAllByText('project-3')[1]);

    await fireEvent.click(screen.getByText('form.assign.action.save'));

    await waitFor(() => {
      expect(mockUpdateStorageAssignment).toHaveBeenCalledWith(storage.id, {
        project_ids: [mockProjects[0].id, mockProjects[2].id],
      });
      expect(toastSuccessMock).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('calls updateStorageAssignment and mix of preselected and disabled to be passed in', async () => {
    mockUpdateStorageAssignment.mockResolvedValueOnce({});

    const mockProjects: Project[] = generateMockProjects(3);

    await act(() =>
      render(
        <AssignStorage
          isOpen
          storage={storage}
          projects={mockProjects}
          selectedProjectIds={[mockProjects[0].id, mockProjects[1].id]}
          disabledProjectIds={[mockProjects[1].id]}
          onClose={onClose}
        />,
        { wrapper },
      ),
    );

    await fireEvent.click(screen.getByText('project-1, project-2'));
    await fireEvent.click(screen.getAllByText('project-1')[1]);
    await fireEvent.click(screen.getAllByText('project-2')[1]);

    await fireEvent.click(screen.getByText('form.assign.action.save'));

    await waitFor(() => {
      expect(mockUpdateStorageAssignment).toHaveBeenCalledWith(storage.id, {
        project_ids: [mockProjects[1].id],
      });
      expect(toastSuccessMock).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('calls updateStorageAssignment and select a project to be passed in', async () => {
    mockUpdateStorageAssignment.mockResolvedValueOnce({});

    const mockProjects: Project[] = generateMockProjects(1);

    await act(() =>
      render(
        <AssignStorage
          isOpen
          storage={storage}
          projects={mockProjects}
          selectedProjectIds={selectedProjectIds}
          disabledProjectIds={[]}
          onClose={onClose}
        />,
        { wrapper },
      ),
    );

    await fireEvent.click(
      screen.getByText('form.assign.field.projectIds.placeholder'),
    );
    const options = await screen.findAllByText('project-1');
    await fireEvent.click(options[1]);

    await fireEvent.click(screen.getByText('form.assign.action.save'));

    await waitFor(() => {
      expect(mockUpdateStorageAssignment).toHaveBeenCalledWith(storage.id, {
        project_ids: [mockProjects[0].id],
      });
      expect(toastSuccessMock).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error toast on mutation error', async () => {
    mockUpdateStorageAssignment.mockRejectedValueOnce(new Error('fail'));

    act(() => {
      render(
        <AssignStorage
          isOpen
          storage={storage}
          projects={projects}
          selectedProjectIds={selectedProjectIds}
          onClose={onClose}
          disabledProjectIds={[]}
        />,
        { wrapper },
      );
    });
    fireEvent.click(screen.getByText('form.assign.action.save'));
    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'form.assign.notification.error',
        expect.any(Error),
      );
    });
  });

  it('calls onClose when cancel button is clicked', () => {
    act(() => {
      render(
        <AssignStorage
          isOpen
          storage={storage}
          projects={projects}
          selectedProjectIds={selectedProjectIds}
          onClose={onClose}
          disabledProjectIds={[]}
        />,
        { wrapper },
      );
    });
    fireEvent.click(screen.getByText('form.assign.action.cancel'));
    expect(onClose).toHaveBeenCalled();
  });
});
