// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import { ProjectStatus } from '@/types/enums/projects';

import { ProjectStatusField } from '@/components/features/projects/ProjectStatusField';

import '@testing-library/jest-dom';

describe('Project StatusField', () => {
  it('renders the correct icon and text for READY status', () => {
    act(() => {
      render(<ProjectStatusField status={ProjectStatus.READY} />);
    });
    expect(
      screen.getByText(`status.${ProjectStatus.READY}`),
    ).toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveClass('fill-success-500');
  });

  it('renders the correct icon and text for PARTIALLY_READY status', () => {
    act(() => {
      render(<ProjectStatusField status={ProjectStatus.PARTIALLY_READY} />);
    });
    expect(
      screen.getByText(`status.${ProjectStatus.PARTIALLY_READY}`),
    ).toBeInTheDocument();
    expect(screen.getByRole('img', { hidden: true })).toHaveClass(
      'stroke-primary-500',
    );
  });

  it('renders the correct icon and text for PENDING status', () => {
    act(() => {
      render(<ProjectStatusField status={ProjectStatus.PENDING} />);
    });
    expect(
      screen.getByText(`status.${ProjectStatus.PENDING}`),
    ).toBeInTheDocument();
    expect(screen.getByRole('img', { hidden: true })).toHaveClass(
      'stroke-primary-500 animate-spin',
    );
  });

  it('renders the correct icon and text for DELETING status', () => {
    act(() => {
      render(<ProjectStatusField status={ProjectStatus.DELETING} />);
    });
    expect(
      screen.getByText(`status.${ProjectStatus.DELETING}`),
    ).toBeInTheDocument();
    expect(screen.getByRole('img', { hidden: true })).toHaveClass(
      'stroke-primary-500 animate-spin',
    );
  });

  it('renders the correct icon and text for FAILED status', () => {
    act(() => {
      render(<ProjectStatusField status={ProjectStatus.FAILED} />);
    });
    expect(
      screen.getByText(`status.${ProjectStatus.FAILED}`),
    ).toBeInTheDocument();
    expect(screen.getByRole('img', { hidden: true })).toHaveClass(
      'fill-danger-500',
    );
  });

  it('renders nothing for an unknown status', () => {
    act(() => {
      render(<ProjectStatusField status={'UNKNOWN' as ProjectStatus} />);
    });
    expect(screen.queryByText(/status./)).not.toBeInTheDocument();
  });

  it('renders a popover with reason if there is one and status is failure', () => {
    act(() => {
      render(
        <ProjectStatusField
          status={ProjectStatus.FAILED}
          statusReason="Here is a reason"
        />,
      );
    });
    const trigger = screen.getByText('(statusReason.messageTrigger)');
    expect(trigger).toBeInTheDocument();
    fireEvent.click(trigger);
    expect(screen.getByText('statusReason.messageHeader')).toBeInTheDocument();
    expect(screen.getByText('Here is a reason')).toBeInTheDocument();
  });

  it('does not render a popover with reason if status is not failure', () => {
    act(() => {
      render(
        <ProjectStatusField
          status={ProjectStatus.READY}
          statusReason="Here is a reason"
        />,
      );
    });
    const trigger = screen.queryByText('(statusReason.messageTrigger)');
    expect(trigger).not.toBeInTheDocument();
  });
});
