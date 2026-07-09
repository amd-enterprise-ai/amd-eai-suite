// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import type { Story, StoryDefault } from '@ladle/react';
import { Textarea } from '../../../src/Textarea';
export default { title: 'Components/Textarea' } satisfies StoryDefault;
export const Default: Story = () => (
  <div className="w-full max-w-md p-4">
    <Textarea
      label="Description"
      placeholder="Enter a description"
      minRows={3}
    />
  </div>
);
export const WithValue: Story = () => (
  <div className="w-full max-w-md p-4">
    <Textarea
      label="Secret value"
      value="pre-filled content"
      minRows={4}
      onChange={() => undefined}
    />
  </div>
);
export const Disabled: Story = () => (
  <div className="w-full max-w-md p-4">
    <Textarea
      label="Description"
      value="Read-only content"
      minRows={3}
      isDisabled
    />
  </div>
);
