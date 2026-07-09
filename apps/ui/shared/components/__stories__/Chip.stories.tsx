// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Chip } from '../src/Chip';

export default { title: 'Components/Chip' } satisfies StoryDefault;

export const Default: Story = () => <Chip>Default</Chip>;

export const Colors: Story = () => (
  <div className="flex flex-wrap gap-2">
    <Chip color="primary">Primary</Chip>
    <Chip color="success">Success</Chip>
  </div>
);

export const Variants: Story = () => (
  <div className="flex flex-wrap gap-2">
    <Chip variant="solid">Solid</Chip>
    <Chip variant="flat">Flat</Chip>
  </div>
);

export const Sizes: Story = () => (
  <div className="flex items-center gap-2">
    <Chip size="sm">Small</Chip>
    <Chip size="lg">Large</Chip>
  </div>
);
