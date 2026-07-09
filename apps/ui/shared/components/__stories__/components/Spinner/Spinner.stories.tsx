// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Spinner } from '../../../src/Spinner';

export default { title: 'Components/Spinner' } satisfies StoryDefault;

export const Default: Story = () => <Spinner />;

export const Sizes: Story = () => (
  <div className="flex items-center gap-4">
    <Spinner size="sm" />
    <Spinner size="md" />
    <Spinner size="lg" />
  </div>
);

export const Colors: Story = () => (
  <div className="flex items-center gap-4">
    <Spinner color="default" />
    <Spinner color="primary" />
    <Spinner color="secondary" />
    <Spinner color="success" />
    <Spinner color="warning" />
    <Spinner color="danger" />
  </div>
);

export const WithLabel: Story = () => <Spinner label="Loading..." />;
