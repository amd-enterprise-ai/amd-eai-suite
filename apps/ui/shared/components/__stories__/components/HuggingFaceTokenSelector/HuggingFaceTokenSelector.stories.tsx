// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';

import {
  HuggingFaceTokenSelector,
  type HuggingFaceTokenSelectorLabels,
} from '../../../src/HuggingFaceTokenSelector/HuggingFaceTokenSelector';

export default {
  title: 'Components/HuggingFaceTokenSelector',
} satisfies StoryDefault;

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

const tokens = [
  { name: 'token-1-hf', displayName: 'token-1-hf' },
  { name: 'customer-acme-2026', displayName: 'customer-acme-2026' },
];

const okCreate = async ({ name }: { name: string }) => {
  await new Promise((resolve) => setTimeout(resolve, 600));
  return { name };
};

const failingCreate = async () => {
  await new Promise((resolve) => setTimeout(resolve, 600));
  throw new Error('Mock backend rejected the request.');
};

export const Empty: Story = () => {
  const [value, setValue] = useState<string | null>(null);
  return (
    <div className="w-full max-w-md p-6">
      <HuggingFaceTokenSelector
        value={value}
        onChange={setValue}
        existingTokens={[]}
        onCreateToken={okCreate}
        labels={labels}
      />
      <p className="mt-3 text-xs text-default-500">Selected: {value ?? '—'}</p>
    </div>
  );
};

export const WithExistingTokens: Story = () => {
  const [value, setValue] = useState<string | null>(null);
  return (
    <div className="w-full max-w-md p-6">
      <HuggingFaceTokenSelector
        value={value}
        onChange={setValue}
        existingTokens={tokens}
        onCreateToken={okCreate}
        labels={labels}
      />
      <p className="mt-3 text-xs text-default-500">Selected: {value ?? '—'}</p>
    </div>
  );
};

export const PreSelected: Story = () => {
  const [value, setValue] = useState<string | null>('customer-acme-2026');
  return (
    <div className="w-full max-w-md p-6">
      <HuggingFaceTokenSelector
        value={value}
        onChange={setValue}
        existingTokens={tokens}
        onCreateToken={okCreate}
        labels={labels}
      />
      <p className="mt-3 text-xs text-default-500">Selected: {value ?? '—'}</p>
    </div>
  );
};

export const CreateTokenFailure: Story = () => {
  const [value, setValue] = useState<string | null>(null);
  return (
    <div className="w-full max-w-md p-6">
      <HuggingFaceTokenSelector
        value={value}
        onChange={setValue}
        existingTokens={tokens}
        onCreateToken={failingCreate}
        labels={labels}
      />
      <p className="mt-3 text-xs text-default-500">
        Open the dropdown → choose &quot;+ Add new&quot; → fill the form →
        submit to see error handling.
      </p>
    </div>
  );
};

export const InvalidWithError: Story = () => {
  const [value, setValue] = useState<string | null>(null);
  return (
    <div className="w-full max-w-md p-6">
      <HuggingFaceTokenSelector
        value={value}
        onChange={setValue}
        existingTokens={tokens}
        onCreateToken={okCreate}
        labels={labels}
        isInvalid
        errorMessage="A token is required to download gated models."
      />
    </div>
  );
};

export const Disabled: Story = () => (
  <div className="w-full max-w-md p-6">
    <HuggingFaceTokenSelector
      value={null}
      onChange={() => undefined}
      existingTokens={tokens}
      onCreateToken={okCreate}
      labels={labels}
      isDisabled
    />
  </div>
);
