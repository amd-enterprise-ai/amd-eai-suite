// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CopySnippet } from '@amdenterpriseai/components';

describe('CopySnippet adapter', () => {
  let writeText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    writeText = vi.fn();
    writeText.mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });
  });

  it('renders the text passed as children', () => {
    render(<CopySnippet>hello-world</CopySnippet>);
    expect(screen.getByText('hello-world')).toBeInTheDocument();
  });

  it('renders the text passed via the value prop', () => {
    render(<CopySnippet value="from-value" />);
    expect(screen.getByText('from-value')).toBeInTheDocument();
  });

  it('writes the value to the clipboard when the copy button is clicked', async () => {
    render(<CopySnippet>copy-me</CopySnippet>);
    fireEvent.click(screen.getByRole('button'));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('copy-me');
    });
  });

  it('hides the copy button when hideCopyButton is set', () => {
    render(<CopySnippet hideCopyButton>no-copy</CopySnippet>);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
