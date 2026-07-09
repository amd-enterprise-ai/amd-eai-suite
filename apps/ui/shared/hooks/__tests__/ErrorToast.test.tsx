// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { ErrorToast } from '@amdenterpriseai/hooks';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('ErrorToast', () => {
  let writeText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });
  });

  it('renders the error content', () => {
    render(
      <ErrorToast
        content="Something went wrong"
        copyText="Something went wrong"
      />,
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('copies the error text to the clipboard when the copy button is clicked', async () => {
    render(<ErrorToast content="Boom" copyText="Boom" />);

    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('Boom');
    });
  });

  it('does not render a copy button when there is no copyable text', () => {
    render(<ErrorToast content={<span>Rich error</span>} />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('keeps the copied feedback visible across rapid repeated clicks', async () => {
    vi.useFakeTimers();
    try {
      render(<ErrorToast content="Boom" copyText="Boom" />);
      const button = screen.getByRole('button');

      // advanceTimersByTimeAsync flushes the clipboard promise's microtask so
      // the `copied` state update lands before each assertion.
      fireEvent.click(button);
      await vi.advanceTimersByTimeAsync(0);
      expect(button).toHaveAttribute('aria-label', 'actions.copy.copied');

      // A second click just before the first window elapses must restart it, so
      // the earlier timer can't clear the feedback early.
      await vi.advanceTimersByTimeAsync(1500);
      fireEvent.click(button);
      await vi.advanceTimersByTimeAsync(1500);
      expect(button).toHaveAttribute('aria-label', 'actions.copy.copied');

      await vi.advanceTimersByTimeAsync(600);
      expect(button).toHaveAttribute('aria-label', 'actions.copy.title');
    } finally {
      vi.useRealTimers();
    }
  });
});
