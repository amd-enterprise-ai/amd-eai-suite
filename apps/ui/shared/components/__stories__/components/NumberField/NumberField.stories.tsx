// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import type { Story, StoryDefault } from '@ladle/react';
import { NumberField, NumberInput } from '../../../src/NumberField';
export default { title: 'Components/NumberField' } satisfies StoryDefault;
export const NumberFieldDefault: Story = () => (
  <div className="w-full max-w-xs p-4">
    <NumberField
      label="Replicas"
      defaultValue={2}
      minValue={0}
      maxValue={10}
      step={1}
    />
  </div>
);
export const NumberInputAlias: Story = () => (
  <div className="w-full max-w-xs p-4">
    <NumberInput
      label="Replicas (v2 alias)"
      defaultValue={1}
      minValue={0}
      maxValue={10}
      step={1}
    />
  </div>
);
export const Disabled: Story = () => (
  <div className="w-full max-w-xs p-4">
    <NumberField label="Replicas" defaultValue={3} step={1} isDisabled />
  </div>
);
