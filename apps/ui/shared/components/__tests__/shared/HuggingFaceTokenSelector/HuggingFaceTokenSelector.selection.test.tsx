// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render } from '@testing-library/react';
import { vi } from 'vitest';

import {
  HuggingFaceTokenSelector,
  type HuggingFaceTokenSelectorLabels,
} from '@/src/HuggingFaceTokenSelector/HuggingFaceTokenSelector';

/**
 * Capture handle for the HeroUI Select stub below. The shared selector
 * passes its `handleSelectionChange` callback into HeroUI's `Select`; this
 * test bypasses the real dropdown UI and invokes the callback directly so it
 * can exercise edge cases (such as the HeroUI `'all'` sentinel) that cannot
 * be triggered from a single-select DOM interaction.
 */
let capturedOnSelectionChange:
  | ((keys: 'all' | Set<unknown>) => void)
  | undefined;

vi.mock('@/src/Select/Select', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/src/Select/Select')>();
  return {
    ...actual,
    Select: (props: {
      onSelectionChange?: (keys: 'all' | Set<unknown>) => void;
    }) => {
      capturedOnSelectionChange = props.onSelectionChange;
      return null;
    },
  };
});

const labels: HuggingFaceTokenSelectorLabels = {
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

describe('HuggingFaceTokenSelector selection handling', () => {
  beforeEach(() => {
    capturedOnSelectionChange = undefined;
  });

  it('ignores HeroUI\'s "all" selection so it never reaches onChange', () => {
    const onChange = vi.fn();

    render(
      <HuggingFaceTokenSelector
        value={null}
        onChange={onChange}
        existingTokens={[{ name: 'token-1', displayName: 'token-1' }]}
        onCreateToken={vi.fn()}
        labels={labels}
      />,
    );

    expect(capturedOnSelectionChange).toBeTypeOf('function');

    expect(() => capturedOnSelectionChange?.('all')).not.toThrow();
    expect(onChange).not.toHaveBeenCalled();
  });

  it('emits the selected token name when HeroUI returns a Set', () => {
    const onChange = vi.fn();

    render(
      <HuggingFaceTokenSelector
        value={null}
        onChange={onChange}
        existingTokens={[{ name: 'token-1', displayName: 'token-1' }]}
        onCreateToken={vi.fn()}
        labels={labels}
      />,
    );

    capturedOnSelectionChange?.(new Set(['token-1']));
    expect(onChange).toHaveBeenCalledWith('token-1');
  });
});
