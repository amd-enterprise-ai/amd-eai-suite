// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { ProjectSecretStatus as ProjectSecretStatusEnum } from '@/types/enums/secrets';

import { ProjectSecretStatus } from '@/components/features/secrets';

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

describe('ProjectSecretStatus', () => {
  it('renders created status with check icon and correct label', () => {
    act(() => {
      render(
        <ProjectSecretStatus
          status={ProjectSecretStatusEnum.SYNCED}
          statusReason={null}
        />,
      );
    });
    expect(screen.getByTestId('icon-check')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${ProjectSecretStatusEnum.SYNCED}`),
    ).toBeInTheDocument();
  });

  it('renders pending status with loader icon and correct label', () => {
    act(() => {
      render(
        <ProjectSecretStatus
          status={ProjectSecretStatusEnum.PENDING}
          statusReason={null}
        />,
      );
    });
    expect(screen.getByTestId('icon-loader')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${ProjectSecretStatusEnum.PENDING}`),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <ProjectSecretStatus
          status={ProjectSecretStatusEnum.SYNCED_ERROR}
          statusReason={'Failed to sync'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${ProjectSecretStatusEnum.SYNCED_ERROR}`),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <ProjectSecretStatus
          status={ProjectSecretStatusEnum.FAILED}
          statusReason={'Some error occurred'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${ProjectSecretStatusEnum.FAILED}`),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders delete failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <ProjectSecretStatus
          status={ProjectSecretStatusEnum.DELETE_FAILED}
          statusReason={'Failed to delete'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${ProjectSecretStatusEnum.DELETE_FAILED}`),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label with no error message', () => {
    act(() => {
      render(
        <ProjectSecretStatus
          status={ProjectSecretStatusEnum.FAILED}
          statusReason={null}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${ProjectSecretStatusEnum.FAILED}`),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('(statusReason.messageTrigger)'),
    ).not.toBeInTheDocument();
  });
});
