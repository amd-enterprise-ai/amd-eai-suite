// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Link } from '../../../src/Link';

export default { title: 'Components/Link' } satisfies StoryDefault;

export const Default: Story = () => <Link href="#">Default link</Link>;

export const Colors: Story = () => (
  <div className="flex flex-col gap-2">
    <Link href="#" color="foreground">
      Foreground
    </Link>
    <Link href="#" color="primary">
      Primary
    </Link>
    <Link href="#" color="secondary">
      Secondary
    </Link>
    <Link href="#" color="success">
      Success
    </Link>
    <Link href="#" color="warning">
      Warning
    </Link>
    <Link href="#" color="danger">
      Danger
    </Link>
  </div>
);
