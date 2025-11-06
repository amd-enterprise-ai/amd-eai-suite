// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import StatusErrorPopover from '@/components/shared/StatusErrorPopover/StatusErrorPopover';

describe('StatusErrorPopover', () => {
  const props = {
    statusReason: 'Some error occurred',
    triggerText: 'Show details',
    headerText: 'Error Details',
  };

  it('renders trigger text', () => {
    act(() => {
      render(<StatusErrorPopover {...props} />);
    });
    expect(screen.getByText(`(${props.triggerText})`)).toBeInTheDocument();
  });

  it('renders header text in popover content', () => {
    act(() => {
      render(<StatusErrorPopover {...props} />);
    });
    fireEvent.click(screen.getByText(`(${props.triggerText})`));
    expect(screen.getByText(props.headerText)).toBeInTheDocument();
  });

  it('renders status reason inside code block', () => {
    act(() => {
      render(<StatusErrorPopover {...props} />);
    });
    fireEvent.click(screen.getByText(`(${props.triggerText})`));
    expect(screen.getByText(props.headerText)).toBeInTheDocument();
    expect(screen.getByText(props.statusReason)).toBeInTheDocument();
  });

  it('renders no status reason when statusReason is null', () => {
    act(() => {
      render(<StatusErrorPopover {...props} statusReason={null} />);
    });
    fireEvent.click(screen.getByText(`(${props.triggerText})`));
    expect(screen.getByText(props.headerText)).toBeInTheDocument();
    expect(screen.queryByText(props.statusReason)).not.toBeInTheDocument();
  });

  it('renders secondary reasons', () => {
    act(() => {
      render(
        <StatusErrorPopover
          {...props}
          secondaryStatusReasons={[
            { key: 'key-1', description: 'Detail 1' },
            { key: 'key-2', description: 'Detail 2' },
          ]}
        />,
      );
    });
    fireEvent.click(screen.getByText(`(${props.triggerText})`));

    expect(screen.getByText(props.headerText)).toBeInTheDocument();
    expect(screen.queryByText(props.statusReason)).toBeInTheDocument();
    expect(screen.getByText('status.errorDetail.title')).toBeInTheDocument();
    expect(screen.getByText('Detail 1')).toBeInTheDocument();
    expect(screen.getByText('key-1')).toBeInTheDocument();

    expect(screen.queryByText('Detail 2')).not.toBeInTheDocument();
    expect(screen.queryByText('key-2')).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('status.errorDetail.action.next'));

    expect(screen.queryByText('Detail 1')).not.toBeInTheDocument();
    expect(screen.queryByText('Detail 2')).toBeInTheDocument();
    expect(screen.queryByText('key-1')).not.toBeInTheDocument();
    expect(screen.queryByText('key-2')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('status.errorDetail.action.prev'));

    expect(screen.queryByText('Detail 1')).toBeInTheDocument();
    expect(screen.queryByText('Detail 2')).not.toBeInTheDocument();
  });
});
