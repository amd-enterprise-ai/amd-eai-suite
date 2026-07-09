// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { zodResolver } from '@hookform/resolvers/zod';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { useForm } from 'react-hook-form';
import { describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { RuntimeProfileKeyValueEditor } from '@/components/features/models/runtime-profile/RuntimeProfileKeyValueEditor';

type FormValues = {
  engineArgs: { key: string; value: string }[];
};

function TestHarness({ onSubmit }: { onSubmit: (values: FormValues) => void }) {
  const form = useForm<FormValues>({
    defaultValues: { engineArgs: [{ key: '', value: '' }] },
    resolver: zodResolver(
      z.object({
        engineArgs: z
          .array(z.object({ key: z.string(), value: z.string() }))
          .superRefine((rows, ctx) => {
            rows.forEach((row, index) => {
              if (row.value.trim() && !row.key.trim()) {
                ctx.addIssue({
                  code: z.ZodIssueCode.custom,
                  message: 'Key required',
                  path: [index, 'key'],
                });
              }
            });
          }),
      }),
    ),
  });
  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      <RuntimeProfileKeyValueEditor<FormValues>
        form={form}
        name="engineArgs"
        keyLabel="Key"
        valueLabel="Value"
        keyPlaceholder="key"
        valuePlaceholder="value"
        addEntryLabel="Add"
        removeEntryLabel="Remove"
        testIdPrefix="test-kv"
      />
      <button type="submit">Submit</button>
    </form>
  );
}

describe('RuntimeProfileKeyValueEditor', () => {
  it('adds rows and blocks submit when key is empty but value is set', async () => {
    const onSubmit = vi.fn();
    render(<TestHarness onSubmit={onSubmit} />);
    await act(async () => {
      fireEvent.click(screen.getByTestId('test-kv-add-row'));
    });
    expect(screen.getByTestId('test-kv-kv-row-1')).toBeInTheDocument();
    await act(async () => {
      fireEvent.change(screen.getByTestId('test-kv-value-0'), {
        target: { value: 'TRITON_ATTN' },
      });
      fireEvent.click(screen.getByText('Submit'));
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
