// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';
import { Checkbox } from '../../../src/Checkbox';
export default { title: 'Components/Checkbox' } satisfies StoryDefault;
export const Unchecked: Story = () => (
  <Checkbox isSelected={false}>Remember</Checkbox>
);
export const Checked: Story = () => <Checkbox isSelected>Remember</Checkbox>;
export const Disabled: Story = () => (
  <div className="flex flex-col gap-4">
    <Checkbox isDisabled isSelected={false}>
      Off
    </Checkbox>
    <Checkbox isDisabled isSelected>
      On
    </Checkbox>
  </div>
);
export const Interactive: Story = () => {
  const [isSelected, setIsSelected] = useState(false);
  return (
    <Checkbox isSelected={isSelected} onValueChange={setIsSelected}>
      Agree
    </Checkbox>
  );
};
