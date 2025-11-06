// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import { SecretStatus as SecretStatusEnum } from '@/types/enums/secrets';

import { SecretStatus } from '@/components/features/secrets';

// Mock @tabler/icons-react
vi.mock('@tabler/icons-react', () => {
  return {
    IconLoaderQuarter: (props: any) => (
      <svg data-testid="icon-loader" {...props} />
    ),
    IconCircleCheckFilled: (props: any) => (
      <svg data-testid="icon-check" {...props} />
    ),
    IconCircleXFilled: (props: any) => <svg data-testid="icon-x" {...props} />,
    IconLineDashed: (props: any) => (
      <svg data-testid="icon-dashed" {...props} />
    ),
    IconChevronLeft: (props: any) => (
      <svg data-testid="icon-chevron-left" {...props} />
    ),
    IconChevronRight: (props: any) => (
      <svg data-testid="icon-chevron-right" {...props} />
    ),
  };
});

describe('SecretStatus', () => {
  it('renders created status with check icon and correct label', () => {
    act(() => {
      render(
        <SecretStatus status={SecretStatusEnum.SYNCED} statusReason={null} />,
      );
    });
    expect(screen.getByTestId('icon-check')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatusEnum.SYNCED}`),
    ).toBeInTheDocument();
  });

  it('renders pending status with loader icon and correct label', () => {
    act(() => {
      render(
        <SecretStatus status={SecretStatusEnum.PENDING} statusReason={null} />,
      );
    });
    expect(screen.getByTestId('icon-loader')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatusEnum.PENDING}`),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <SecretStatus
          status={SecretStatusEnum.SYNCED_ERROR}
          statusReason={'Failed to sync'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatusEnum.SYNCED_ERROR}`),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <SecretStatus
          status={SecretStatusEnum.FAILED}
          statusReason={'Some error occurred'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatusEnum.FAILED}`),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders delete failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <SecretStatus
          status={SecretStatusEnum.DELETE_FAILED}
          statusReason={'Failed to delete'}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatusEnum.DELETE_FAILED}`),
    ).toBeInTheDocument();
    expect(
      screen.getByText('(statusReason.messageTrigger)'),
    ).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label with no error message', () => {
    act(() => {
      render(
        <SecretStatus status={SecretStatusEnum.FAILED} statusReason={null} />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatusEnum.FAILED}`),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('(statusReason.messageTrigger)'),
    ).not.toBeInTheDocument();
  });

  it('renders unassigned status with dashed icon and no label', () => {
    act(() => {
      render(
        <SecretStatus
          status={SecretStatusEnum.UNASSIGNED}
          statusReason={null}
        />,
      );
    });
    expect(screen.getByTestId('icon-dashed')).toBeInTheDocument();
  });

  it('renders sync failed status with x icon and correct label and error message', () => {
    act(() => {
      render(
        <SecretStatus
          status={SecretStatusEnum.SYNCED_ERROR}
          statusReason={'Failed to sync'}
          secondaryStatusReason={[
            { key: 'project-1', description: 'first secondary reason' },
            { key: 'project-2', description: 'second secondary reason' },
          ]}
        />,
      );
    });
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
    expect(
      screen.getByText(`secretStatus.${SecretStatusEnum.SYNCED_ERROR}`),
    ).toBeInTheDocument();

    const errorMessageTrigger = screen.getByText(
      '(statusReason.messageTrigger)',
    );
    expect(errorMessageTrigger).toBeInTheDocument();

    fireEvent.click(errorMessageTrigger);

    expect(screen.getByText('project-1')).toBeInTheDocument();
    expect(screen.getByText('first secondary reason')).toBeInTheDocument();
  });
});
