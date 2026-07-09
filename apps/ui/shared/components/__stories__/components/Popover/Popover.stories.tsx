// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Popover, PopoverContent, PopoverTrigger } from '../../../src/Popover';

export default {
  title: 'Components/Popover',
} satisfies StoryDefault;

export const Basic: Story = () => (
  <Popover placement="bottom">
    <PopoverTrigger>
      <button
        type="button"
        className="px-4 py-2 bg-primary text-white rounded-md text-sm"
      >
        Open Popover
      </button>
    </PopoverTrigger>
    <PopoverContent>
      <div className="px-1 py-2">
        <p className="text-sm">Popover content goes here.</p>
      </div>
    </PopoverContent>
  </Popover>
);

export const CompoundForm: Story = () => (
  <Popover placement="bottom">
    <Popover.Trigger>
      <button
        type="button"
        className="px-4 py-2 bg-primary text-white rounded-md text-sm"
      >
        Compound Popover
      </button>
    </Popover.Trigger>
    <Popover.Content>
      <div className="px-1 py-2">
        <p className="text-sm">
          Rendered via Popover.Trigger and Popover.Content.
        </p>
      </div>
    </Popover.Content>
  </Popover>
);
