// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { HuggingFaceTokenDrawer } from '@/components/features/models/HuggingFaceTokenDrawer';

import wrapper from '@/__tests__/ProviderWrapper';

vi.mock('@/utils/app/huggingface-secret', async () => {
  const actual = await vi.importActual('@/utils/app/huggingface-secret');
  return {
    ...actual,
    isValidHuggingFaceToken: vi.fn((token: string) => {
      const hfTokenPattern = /^hf_[a-zA-Z0-9]{20,}$/;
      return hfTokenPattern.test(token);
    }),
  };
});

describe('HuggingFaceTokenDrawer', () => {
  const mockExistingTokens = [
    { id: 'token-1', name: 'Production Token' },
    { id: 'token-2', name: 'Development Token' },
  ];

  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onApply: vi.fn(),
    existingTokens: mockExistingTokens,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the drawer with title and form elements when open', () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      expect(
        screen.getByText('huggingFaceTokenDrawer.title'),
      ).toBeInTheDocument();
      expect(
        screen.getAllByText(
          'huggingFaceTokenDrawer.fields.selectToken.label',
        )[0],
      ).toBeInTheDocument();
      expect(
        screen.getByRole('tab', {
          name: 'huggingFaceTokenDrawer.fields.addNew',
        }),
      ).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      const { container } = render(
        <HuggingFaceTokenDrawer {...defaultProps} isOpen={false} />,
        { wrapper },
      );
      expect(container).toBeEmptyDOMElement();
    });

    it('renders cancel and apply buttons', () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      expect(
        screen.getByText('huggingFaceTokenDrawer.actions.cancel'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('huggingFaceTokenDrawer.actions.apply'),
      ).toBeInTheDocument();
    });

    it('renders existing tokens in dropdown', () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      const selectButton = screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken/i,
      });
      fireEvent.click(selectButton);

      expect(screen.getAllByText('Production Token').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Development Token').length).toBeGreaterThan(
        0,
      );
    });

    it('renders tab switcher between select existing and create new modes', () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      expect(
        screen.getByRole('tab', {
          name: 'huggingFaceTokenDrawer.fields.selectExisting',
        }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('tab', {
          name: 'huggingFaceTokenDrawer.fields.addNew',
        }),
      ).toBeInTheDocument();
    });
  });

  describe('Form Interactions - Select Existing Token', () => {
    it('allows selecting an existing token from dropdown', async () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      const selectButton = screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken/i,
      });

      await act(async () => {
        fireEvent.click(selectButton);
      });

      await act(async () => {
        const options = screen.getAllByText('Production Token');
        fireEvent.click(options[options.length - 1]);
      });

      await waitFor(() => {
        expect(selectButton).toHaveTextContent('Production Token');
      });
    });

    it('hides name and token fields when existing token is selected', async () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      // Switch to NEW tab first to make name and token fields visible
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      // Verify fields are visible in NEW tab
      expect(
        screen.getByLabelText('huggingFaceTokenDrawer.fields.name.label'),
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText('huggingFaceTokenDrawer.fields.token.label'),
      ).toBeInTheDocument();

      // Switch back to EXISTING tab
      const existingTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.selectExisting',
      });
      await act(async () => {
        fireEvent.click(existingTab);
      });

      const selectButton = screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken/i,
      });

      await act(async () => {
        fireEvent.click(selectButton);
      });

      await act(async () => {
        const options = screen.getAllByText('Production Token');
        fireEvent.click(options[options.length - 1]);
      });

      // Fields should now be hidden (we're in EXISTING tab)
      await waitFor(() => {
        expect(
          screen.queryByLabelText('huggingFaceTokenDrawer.fields.name.label'),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByLabelText('huggingFaceTokenDrawer.fields.token.label'),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Interactions - Create New Token', () => {
    it('allows entering name and token for new token', async () => {
      const user = userEvent.setup();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );

      await user.type(nameInput, 'My New Token');
      await user.type(tokenInput, 'hf_abcdefghijklmnopqrstuvwxyz1234567890');

      expect(nameInput).toHaveValue('My New Token');
      expect(tokenInput).toHaveValue('hf_abcdefghijklmnopqrstuvwxyz1234567890');
    });

    it('shows name as required field when creating new token', async () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      expect(nameInput).toHaveAttribute('required');
    });

    it('shows token as required field when creating new token', async () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );
      expect(tokenInput).toHaveAttribute('required');
    });

    it('shows token field as password type', async () => {
      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} />, { wrapper });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );
      expect(tokenInput).toHaveAttribute('type', 'password');
    });
  });

  describe('Validation', () => {
    it('prevents submission when neither existing token nor new token data is provided', async () => {
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab first
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });

    it('prevents submission when only name is provided without token', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      await user.type(nameInput, 'My Token');

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });

    it('prevents submission when only token is provided without name', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );
      await user.type(tokenInput, 'hf_abcdefghijklmnopqrstuvwxyz1234567890');

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });

    it('prevents submission for invalid token format', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );

      await user.type(nameInput, 'My Token');
      await user.type(tokenInput, 'invalid-token-format');

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });

    it('accepts valid Hugging Face token format (hf_*)', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );

      await user.type(nameInput, 'valid-token');
      await user.type(tokenInput, 'hf_abcdefghijklmnopqrstuvwxyz1234567890');

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).toHaveBeenCalledWith({
          name: 'valid-token',
          token: 'hf_abcdefghijklmnopqrstuvwxyz1234567890',
        });
      });
    });

    it('rejects token with invalid prefix', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );

      await user.type(nameInput, 'My Token');
      await user.type(tokenInput, 'invalid_abcdefghijklmnopqrstuvwxyz123456');

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });

    it('rejects token that is too short', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );

      await user.type(nameInput, 'My Token');
      await user.type(tokenInput, 'hf_short');

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });
  });

  describe('Form Submission', () => {
    it('calls onApply and onClose with selected token data', async () => {
      const onApply = vi.fn();
      const onClose = vi.fn();

      act(() => {
        render(
          <HuggingFaceTokenDrawer
            {...defaultProps}
            onApply={onApply}
            onClose={onClose}
          />,
          { wrapper },
        );
      });

      const selectButton = screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken/i,
      });

      await act(async () => {
        fireEvent.click(selectButton);
      });

      await act(async () => {
        const options = screen.getAllByText('Production Token');
        fireEvent.click(options[options.length - 1]);
      });

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).toHaveBeenCalledWith(
          expect.objectContaining({
            selectedToken: 'token-1',
          }),
        );
        expect(onClose).toHaveBeenCalled();
      });
    });

    it('calls onApply and onClose with new token data', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();
      const onClose = vi.fn();

      act(() => {
        render(
          <HuggingFaceTokenDrawer
            {...defaultProps}
            onApply={onApply}
            onClose={onClose}
          />,
          { wrapper },
        );
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );

      await user.type(nameInput, 'new-token');
      await user.type(tokenInput, 'hf_newtoken1234567890abcdefghijklmnop');

      const applyButton = screen.getByRole('button', {
        name: 'huggingFaceTokenDrawer.actions.apply',
      });

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).toHaveBeenCalledWith({
          name: 'new-token',
          token: 'hf_newtoken1234567890abcdefghijklmnop',
        });
        expect(onClose).toHaveBeenCalled();
      });
    });

    it('does not call onApply when validation fails', async () => {
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      const applyButton = screen.getByRole('button', {
        name: 'huggingFaceTokenDrawer.actions.apply',
      });

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });
  });

  describe('Cancel Action', () => {
    it('calls onClose when cancel button is clicked', async () => {
      const onClose = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onClose={onClose} />, {
          wrapper,
        });
      });

      const cancelButton = screen.getByRole('button', {
        name: 'huggingFaceTokenDrawer.actions.cancel',
      });

      await act(async () => {
        fireEvent.click(cancelButton);
      });

      expect(onClose).toHaveBeenCalled();
    });

    it('does not call onApply when cancel is clicked', async () => {
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      const cancelButton = screen.getByRole('button', {
        name: 'huggingFaceTokenDrawer.actions.cancel',
      });

      await act(async () => {
        fireEvent.click(cancelButton);
      });

      expect(onApply).not.toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty existing tokens array', () => {
      act(() => {
        render(
          <HuggingFaceTokenDrawer {...defaultProps} existingTokens={[]} />,
          { wrapper },
        );
      });

      // When no existing tokens, should default to NEW tab which shows name/token fields
      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );

      expect(nameInput).toBeInTheDocument();
    });

    it('handles whitespace-only input in name field', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );

      await user.type(nameInput, '   ');
      await user.type(tokenInput, 'hf_abcdefghijklmnopqrstuvwxyz1234567890');

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });

    it('handles whitespace-only input in token field', async () => {
      const user = userEvent.setup();
      const onApply = vi.fn();

      act(() => {
        render(<HuggingFaceTokenDrawer {...defaultProps} onApply={onApply} />, {
          wrapper,
        });
      });

      // Switch to NEW tab to access name/token fields
      const newTab = screen.getByRole('tab', {
        name: 'huggingFaceTokenDrawer.fields.addNew',
      });
      await act(async () => {
        fireEvent.click(newTab);
      });

      const nameInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.name.label',
      );
      const tokenInput = screen.getByLabelText(
        'huggingFaceTokenDrawer.fields.token.label',
      );

      await user.type(nameInput, 'My Token');
      await user.type(tokenInput, '   ');

      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).not.toHaveBeenCalled();
      });
    });

    it('allows submission after selecting an existing token', async () => {
      const onApply = vi.fn();
      const onClose = vi.fn();

      act(() => {
        render(
          <HuggingFaceTokenDrawer
            {...defaultProps}
            onApply={onApply}
            onClose={onClose}
          />,
          { wrapper },
        );
      });

      // Select an existing token
      const selectButton = screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken/i,
      });

      await act(async () => {
        fireEvent.click(selectButton);
      });

      await act(async () => {
        const options = screen.getAllByText('Production Token');
        fireEvent.click(options[options.length - 1]);
      });

      // Should be able to submit
      const applyButton = screen.getByText(
        'huggingFaceTokenDrawer.actions.apply',
      );

      await act(async () => {
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(onApply).toHaveBeenCalled();
        expect(onClose).toHaveBeenCalled();
      });
    });
  });
});
