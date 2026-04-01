// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import SystemToastContainer from '../../../../components/shared/SystemToastContainer/SystemToastContainer';

// Mock next-themes useTheme
vi.mock('next-themes', () => ({
  useTheme: () => ({ theme: 'light' }),
}));

// Mock react-toastify ToastContainer
vi.mock('react-toastify', async () => {
  const actual = await vi.importActual<any>('react-toastify');
  return {
    ...actual,
    ToastContainer: (props: any) => (
      <div data-testid="toast-container" {...props}>
        {props.closeButton}
      </div>
    ),
    Bounce: 'Bounce',
  };
});

// Mock @tabler/icons-react IconX
vi.mock('@tabler/icons-react', () => ({
  IconX: (props: any) => <svg data-testid="icon-x" {...props} />,
}));

describe('SystemToastContainer', () => {
  it('renders ToastContainer with correct props', () => {
    render(<SystemToastContainer />);
    const toastContainer = screen.getByTestId('toast-container');
    expect(toastContainer).toBeInTheDocument();
    expect(toastContainer).toHaveAttribute('position', 'top-right');
    expect(toastContainer).toHaveAttribute('autoClose', '5000');
    expect(toastContainer).toHaveAttribute('draggable');
    expect(toastContainer).toHaveAttribute('transition', 'Bounce');
    expect(toastContainer).toHaveAttribute('theme', 'light');
  });

  it('renders custom close button', () => {
    render(<SystemToastContainer />);
    expect(screen.getByTestId('icon-x')).toBeInTheDocument();
  });
});
