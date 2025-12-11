// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import StatusError from '@/components/shared/StatusError/StatusError';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock @heroui/react Button
vi.mock('@heroui/react', () => ({
  Button: ({
    children,
    onPress,
    isDisabled,
    'aria-label': ariaLabel,
    isIconOnly,
  }: any) => (
    <button
      onClick={onPress}
      disabled={isDisabled}
      aria-label={ariaLabel}
      data-testid={isIconOnly ? 'icon-button' : 'button'}
    >
      {children}
    </button>
  ),
}));

// Mock @tabler/icons-react
vi.mock('@tabler/icons-react', () => ({
  IconChevronLeft: (props: any) => (
    <svg data-testid="icon-chevron-left" {...props} />
  ),
  IconChevronRight: (props: any) => (
    <svg data-testid="icon-chevron-right" {...props} />
  ),
}));

describe('StatusError', () => {
  const props = {
    statusReason: 'Some error occurred',
  };

  it('renders header text', () => {
    act(() => {
      render(<StatusError {...props} />);
    });
    expect(screen.getByText('status.description')).toBeInTheDocument();
  });

  it('renders status reason inside code block', () => {
    act(() => {
      render(<StatusError {...props} />);
    });
    expect(screen.getByText('status.description')).toBeInTheDocument();
    expect(screen.getByText(props.statusReason)).toBeInTheDocument();
  });

  it('renders no status reason when statusReason is null', () => {
    act(() => {
      render(<StatusError {...props} statusReason={null} />);
    });
    expect(screen.getByText('status.description')).toBeInTheDocument();
    expect(screen.queryByText(props.statusReason)).not.toBeInTheDocument();
  });

  it('renders secondary reasons', () => {
    act(() => {
      render(
        <StatusError
          {...props}
          secondaryStatusReasons={[
            { key: 'key-1', description: 'Detail 1' },
            { key: 'key-2', description: 'Detail 2' },
          ]}
        />,
      );
    });

    expect(screen.getByText('status.description')).toBeInTheDocument();
    expect(screen.queryByText(props.statusReason)).toBeInTheDocument();
    expect(screen.getByText('status.errorDetail.title')).toBeInTheDocument();
    expect(screen.getByText('Detail 1')).toBeInTheDocument();
    expect(screen.getByText('key-1')).toBeInTheDocument();

    expect(screen.queryByText('Detail 2')).not.toBeInTheDocument();
    expect(screen.queryByText('key-2')).not.toBeInTheDocument();

    const nextButton = screen.getByLabelText('status.errorDetail.action.next');
    fireEvent.click(nextButton);

    expect(screen.queryByText('Detail 1')).not.toBeInTheDocument();
    expect(screen.queryByText('Detail 2')).toBeInTheDocument();
    expect(screen.queryByText('key-1')).not.toBeInTheDocument();
    expect(screen.queryByText('key-2')).toBeInTheDocument();

    const prevButton = screen.getByLabelText('status.errorDetail.action.prev');
    fireEvent.click(prevButton);

    expect(screen.queryByText('Detail 1')).toBeInTheDocument();
    expect(screen.queryByText('Detail 2')).not.toBeInTheDocument();
  });
});
