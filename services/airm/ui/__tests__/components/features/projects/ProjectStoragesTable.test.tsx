// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { act, render, screen } from '@testing-library/react';

import { fetchProjectStorages } from '@/services/app/storages';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';
import { generateMockProjectStoragesWithParentStorage } from '@/__mocks__/utils/storages-mock';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';

import { ProjectStorageStatus } from '@/types/enums/storages';

import { ProjectStoragesTable } from '@/components/features/projects';

import wrapper from '@/__tests__/ProviderWrapper';
import { cloneDeep } from 'lodash';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({ toast: mockToast }),
}));

vi.mock('@/services/app/storages', () => ({
  fetchProjectStorages: vi.fn(),
}));

describe('ProjectStoragesTable', () => {
  const project = generateMockProjects(1)[0];

  const setup = (
    props?: Partial<React.ComponentProps<typeof ProjectStoragesTable>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <ProjectStoragesTable
          projectId={project.id}
          projectStorages={[]}
          {...props}
        />,
        {
          wrapper,
        },
      );
    });
    return { onOpenChange };
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('default render', () => {
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
    expect(fetchProjectStorages).toHaveBeenCalled();
  });

  it('render with data', () => {
    setup({ projectStorages: generateMockProjectStoragesWithParentStorage(1) });
    expect(screen.getByText('Storage 0')).toBeInTheDocument();
  });

  it('refetches the data if project storage is pending', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const mockProjectStorages = generateMockProjectStoragesWithParentStorage(1);
    mockProjectStorages[0].status = ProjectStorageStatus.PENDING;

    // Immediately after page load
    vi.mocked(fetchProjectStorages).mockResolvedValueOnce({
      projectStorages: mockProjectStorages,
    });

    let syncedProjectStorages = cloneDeep(mockProjectStorages);
    syncedProjectStorages[0].status = ProjectStorageStatus.SYNCED;
    // After 10 seconds, synced
    vi.mocked(fetchProjectStorages).mockResolvedValueOnce({
      projectStorages: syncedProjectStorages,
    });

    await act(async () => {
      render(
        <ProjectStoragesTable
          projectId={project.id}
          projectStorages={mockProjectStorages}
        />,
        {
          wrapper,
        },
      );
    });

    // On page load
    expect(fetchProjectStorages).toBeCalledTimes(1);

    // After 10 seconds, synced storages
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(fetchProjectStorages).toBeCalledTimes(2);

    // No more polling
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(fetchProjectStorages).toBeCalledTimes(2);

    vi.useRealTimers();
  });
});
