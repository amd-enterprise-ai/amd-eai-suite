// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import type { Story, StoryDefault } from '@ladle/react';
import { Divider, Separator } from '../../../src/Separator';
export default { title: 'Components/Separator' } satisfies StoryDefault;
export const HorizontalSeparator: Story = () => (
  <div className="flex w-full max-w-md flex-col gap-4 p-4">
    <p className="text-sm">Above</p>
    <Separator />
    <p className="text-sm">Below</p>
  </div>
);
export const VerticalDivider: Story = () => (
  <div className="flex h-16 items-center gap-4 p-4">
    <span className="text-sm">Left</span>
    <Divider orientation="vertical" className="h-8" />
    <span className="text-sm">Right</span>
  </div>
);
