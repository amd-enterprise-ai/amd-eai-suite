// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import React from 'react';
import { Tooltip } from '../src/Tooltip';

export default { title: 'Components/Tooltip' } satisfies StoryDefault;

export const Default: Story = () => (
  <div className="p-8">
    <Tooltip content="Additional information">
      <button
        type="button"
        className="rounded bg-primary px-3 py-1 text-primary-foreground"
      >
        Hover me
      </button>
    </Tooltip>
  </div>
);
