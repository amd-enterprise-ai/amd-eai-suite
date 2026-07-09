// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Input } from '../../../src/Input/InputPrimitive';

export default { title: 'Components/Input' } satisfies StoryDefault;
export const Default: Story = () => (
  <Input label="Label" placeholder="Enter text…" />
);
export const WithValue: Story = () => (
  <Input label="Label" value="Prefilled value" onChange={() => {}} />
);
export const Invalid: Story = () => (
  <Input
    label="Email"
    placeholder="you@example.com"
    isInvalid
    errorMessage="Invalid email address"
  />
);
export const Disabled: Story = () => (
  <Input label="Disabled" placeholder="Cannot edit" isDisabled />
);
