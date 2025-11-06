// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { act, render, screen } from '@testing-library/react';

import { ProjectStorageStatus as ProjectStorageStatusEnum } from '@/types/enums/storages';

import { ProjectStorageStatus } from '@/components/features/storages';

// Mock @tabler/icons-react
vi.mock('@tabler/icons-react', () => ({
  IconLoaderQuarter: (props: any) => (
    <svg data-testid="icon-loader" {...props} />
  ),
  IconCircleCheckFilled: (props: any) => (
    <svg data-testid="icon-check" {...props} />
  ),
  IconCircleXFilled: (props: any) => <svg data-testid="icon-x" {...props} />,
  IconLineDashed: (props: any) => <svg data-testid="icon-dashed" {...props} />,
}));

describe('ProjectStorageStatus', () => {
  const statusStringPrefix = 'storageStatus';

  it('renders created status with check icon and correct label', () => {
    act(() => {
      render(
        <ProjectStorageStatus
          status={ProjectStorageStatusEnum.SYNCED}
          statusReason={null}
        />,
      );
    });
    expect(screen.getByTestId('icon-check')).toBeInTheDocument();
    expect(
      screen.getByText(
        `${statusStringPrefix}.${ProjectStorageStatusEnum.SYNCED}`,
      ),
    ).toBeInTheDocument();
  });

  it('renders pending status with loader icon and correct label', () => {
    act(() => {
      render(
        <ProjectStorageStatus
          status={ProjectStorageStatusEnum.PENDING}
          statusReason={null}
        />,
      );
    });
    expect(screen.getByTestId('icon-loader')).toBeInTheDocument();
    expect(
      screen.getByText(
        `${statusStringPrefix}.${ProjectStorageStatusEnum.PENDING}`,
      ),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <ProjectStorageStatus
          status={ProjectStorageStatusEnum.SYNCED_ERROR}
          statusReason={'Failed to sync'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(
        `${statusStringPrefix}.${ProjectStorageStatusEnum.SYNCED_ERROR}`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <ProjectStorageStatus
          status={ProjectStorageStatusEnum.FAILED}
          statusReason={'Some error occurred'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(
        `${statusStringPrefix}.${ProjectStorageStatusEnum.FAILED}`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders delete failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <ProjectStorageStatus
          status={ProjectStorageStatusEnum.DELETE_FAILED}
          statusReason={'Failed to delete'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(
        `${statusStringPrefix}.${ProjectStorageStatusEnum.DELETE_FAILED}`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label with no error message', () => {
    act(() => {
      render(
        <ProjectStorageStatus
          status={ProjectStorageStatusEnum.FAILED}
          statusReason={null}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(
        `${statusStringPrefix}.${ProjectStorageStatusEnum.FAILED}`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('(statusReason.messageTrigger)'),
    ).not.toBeInTheDocument();
  });
});
