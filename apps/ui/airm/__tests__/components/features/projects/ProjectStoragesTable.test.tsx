// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { act, render, screen } from '@testing-library/react';

import { fetchProjectStorages } from '@/services/app';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';
import { generateMockProjectStoragesWithParentStorage } from '@/__mocks__/utils/storages-mock';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@amdenterpriseai/utils/app';

import { ProjectStorageStatus } from '@amdenterpriseai/types';

import { ProjectStoragesTable } from '@/components/features/projects';

import wrapper from '@/__tests__/ProviderWrapper';
import { cloneDeep } from 'lodash';

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};
vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@amdenterpriseai/hooks')>()),
  useSystemToast: () => ({ toast: mockToast }),
  useAccessControl: () => ({ isAdministrator: true }),
}));

describe('ProjectStoragesTable', () => {
  const setup = (
    props?: Partial<React.ComponentProps<typeof ProjectStoragesTable>>,
  ) => {
    const onOpenChange = vi.fn();
    act(() => {
      render(
        <ProjectStoragesTable
          isLoading={false}
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
  });

  it('render with data', () => {
    setup({ projectStorages: generateMockProjectStoragesWithParentStorage(1) });
    expect(screen.getByText('Storage 0')).toBeInTheDocument();
  });
});
