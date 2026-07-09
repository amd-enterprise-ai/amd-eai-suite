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
import { vi } from 'vitest';

import {
  HuggingFaceTokenSelector,
  HuggingFaceTokenSelectorLabels,
  HuggingFaceTokenSelectorProps,
} from '@/src/HuggingFaceTokenSelector/HuggingFaceTokenSelector';

const defaultLabels: HuggingFaceTokenSelectorLabels = {
  selectLabel: 'Hugging Face token',
  selectPlaceholder: 'Select a token',
  addNewItemLabel: 'Add new Hugging Face token',
  dialogTitle: 'Add Hugging Face token',
  dialogNameLabel: 'Name',
  dialogNamePlaceholder: 'my-hf-token',
  dialogTokenLabel: 'Token',
  dialogTokenPlaceholder: 'hf_...',
  dialogCancelLabel: 'Cancel',
  dialogSubmitLabel: 'Add token',
};

const existingTokens = [
  { name: 'token-1-hf', displayName: 'token-1-hf' },
  { name: 'customer-acme-2026', displayName: 'customer-acme-2026' },
];

const renderSelector = (
  overrides: Partial<HuggingFaceTokenSelectorProps> = {},
) => {
  const onChange = vi.fn();
  const onCreateToken = vi.fn(async ({ name }: { name: string }) => ({
    name,
  }));

  render(
    <HuggingFaceTokenSelector
      value={null}
      onChange={onChange}
      existingTokens={existingTokens}
      onCreateToken={onCreateToken}
      labels={defaultLabels}
      {...overrides}
    />,
  );

  return { onChange, onCreateToken };
};

const openDropdown = async () => {
  const trigger = screen.getByRole('button', { name: /Hugging Face token/i });
  await act(async () => {
    fireEvent.click(trigger);
  });
};

const clickAddNew = async () => {
  await waitFor(() => {
    expect(screen.getByTestId('hf-token-selector-add-new')).toBeInTheDocument();
  });
  await act(async () => {
    fireEvent.click(screen.getByTestId('hf-token-selector-add-new'));
  });
  await waitFor(() => {
    expect(screen.getByText('Add Hugging Face token')).toBeInTheDocument();
  });
};

describe('HuggingFaceTokenSelector', () => {
  it('renders the select with the configured label and placeholder', () => {
    renderSelector();
    expect(screen.getAllByText('Hugging Face token').length).toBeGreaterThan(0);
    expect(screen.getByText('Select a token')).toBeInTheDocument();
  });

  it('lists existing tokens and the add-new sentinel in the listbox', async () => {
    renderSelector();
    await openDropdown();

    await waitFor(() => {
      expect(screen.getAllByText('token-1-hf').length).toBeGreaterThan(0);
      expect(screen.getAllByText('customer-acme-2026').length).toBeGreaterThan(
        0,
      );
      expect(
        screen.getByTestId('hf-token-selector-add-new'),
      ).toBeInTheDocument();
    });
  });

  it('opens the add-new dialog when the sentinel item is selected', async () => {
    renderSelector();
    await openDropdown();
    await clickAddNew();

    expect(screen.getByText('Add Hugging Face token')).toBeInTheDocument();
  });

  it('submits a new token, auto-selects it, and closes the dialog on success', async () => {
    const onCreateToken = vi.fn(async ({ name }: { name: string }) => ({
      name,
    }));
    const onChange = vi.fn();

    render(
      <HuggingFaceTokenSelector
        value={null}
        onChange={onChange}
        existingTokens={existingTokens}
        onCreateToken={onCreateToken}
        labels={defaultLabels}
      />,
    );

    await openDropdown();
    await clickAddNew();

    fireEvent.change(screen.getByTestId('hf-token-selector-dialog-name'), {
      target: { value: 'my-new-token' },
    });
    fireEvent.change(screen.getByTestId('hf-token-selector-dialog-token'), {
      target: { value: 'hf_secretvalue' },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('hf-token-selector-dialog-submit'));
    });

    await waitFor(() => {
      expect(onCreateToken).toHaveBeenCalledWith({
        name: 'my-new-token',
        token: 'hf_secretvalue',
      });
      expect(onChange).toHaveBeenCalledWith('my-new-token');
    });
  });

  it('shows an error message and stays open when create fails', async () => {
    const onCreateToken = vi
      .fn<HuggingFaceTokenSelectorProps['onCreateToken']>()
      .mockRejectedValue(new Error('Server rejected'));

    renderSelector({ onCreateToken });

    await openDropdown();
    await clickAddNew();

    fireEvent.change(screen.getByTestId('hf-token-selector-dialog-name'), {
      target: { value: 'broken' },
    });
    fireEvent.change(screen.getByTestId('hf-token-selector-dialog-token'), {
      target: { value: 'hf_bad' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('hf-token-selector-dialog-submit'));
    });

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Server rejected');
      // Dialog remains open after error.
      expect(screen.getByText('Add Hugging Face token')).toBeInTheDocument();
    });
  });

  it('disables submit until both name and token are filled', async () => {
    renderSelector();

    await openDropdown();
    await clickAddNew();

    const submit = screen.getByTestId('hf-token-selector-dialog-submit');
    expect(submit).toBeDisabled();

    fireEvent.change(screen.getByTestId('hf-token-selector-dialog-name'), {
      target: { value: 'name-only' },
    });
    expect(submit).toBeDisabled();

    fireEvent.change(screen.getByTestId('hf-token-selector-dialog-token'), {
      target: { value: 'hf_x' },
    });
    expect(submit).not.toBeDisabled();
  });
});
