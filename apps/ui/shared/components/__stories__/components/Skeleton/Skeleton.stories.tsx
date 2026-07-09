// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Skeleton } from '../../../src/Skeleton';

export default { title: 'Components/Skeleton' } satisfies StoryDefault;

export const Default: Story = () => (
  <div className="flex w-full max-w-md flex-col gap-3 p-4">
    <Skeleton className="h-4 w-3/4 rounded-lg" />
    <Skeleton className="h-4 w-full rounded-lg" />
    <Skeleton className="h-4 w-1/2 rounded-lg" />
  </div>
);

export const Loaded: Story = () => (
  <Skeleton isLoaded className="rounded-lg">
    <p className="text-sm">Loaded content</p>
  </Skeleton>
);
