// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { act, render, screen } from '@testing-library/react';

import { fetchProjectSecrets } from '@/services/app/secrets';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';
import { generateMockProjectSecretsWithParentSecret } from '../../../../__mocks__/utils/secrets-mock';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';

import { ProjectSecretStatus } from '@/types/enums/secrets';

import { ProjectSecretsTable } from '@/components/features/projects/ProjectSecretsTable';

import wrapper from '@/__tests__/ProviderWrapper';
import { cloneDeep } from 'lodash';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({ toast: mockToast }),
}));

vi.mock('@/services/app/secrets', () => ({
  fetchProjectSecrets: vi.fn(),
}));

describe('ProjectSecretsTable', () => {
  const project = generateMockProjects(1)[0];

  const setup = (
    props?: Partial<React.ComponentProps<typeof ProjectSecretsTable>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <ProjectSecretsTable
          projectId={project.id}
          projectSecrets={[]}
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
      screen.getByText('list.headers.updatedAt.title'),
    ).toBeInTheDocument();
    expect(fetchProjectSecrets).toHaveBeenCalled();
  });

  it('render with data', () => {
    setup({ projectSecrets: generateMockProjectSecretsWithParentSecret(1) });
    expect(screen.getByText('My Secret 1')).toBeInTheDocument();
  });

  it('refetches the data if project secret is pending', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const mockProjectSecrets = generateMockProjectSecretsWithParentSecret(1);
    mockProjectSecrets[0].status = ProjectSecretStatus.PENDING;

    // Immediately after page load
    vi.mocked(fetchProjectSecrets).mockResolvedValueOnce({
      projectSecrets: mockProjectSecrets,
    });

    let syncedProjectSecrets = cloneDeep(mockProjectSecrets);
    syncedProjectSecrets[0].status = ProjectSecretStatus.SYNCED;
    // After 10 seconds, synced
    vi.mocked(fetchProjectSecrets).mockResolvedValueOnce({
      projectSecrets: syncedProjectSecrets,
    });

    await act(async () => {
      render(
        <ProjectSecretsTable
          projectId={project.id}
          projectSecrets={mockProjectSecrets}
        />,
        {
          wrapper,
        },
      );
    });

    // On page load
    expect(fetchProjectSecrets).toBeCalledTimes(1);

    // After 10 seconds, synced secret
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(fetchProjectSecrets).toBeCalledTimes(2);

    // No more polling
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(fetchProjectSecrets).toBeCalledTimes(2);

    vi.useRealTimers();
  });
});
