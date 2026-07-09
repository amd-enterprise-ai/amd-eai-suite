// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';
import { Pagination } from '../../../src/Pagination';

export default { title: 'Components/Pagination' } satisfies StoryDefault;

export const Default: Story = () => (
  <Pagination showControls page={1} total={10} />
);

export const Bordered: Story = () => (
  <Pagination showControls variant="bordered" size="sm" page={2} total={8} />
);

export const Interactive: Story = () => {
  const [page, setPage] = useState(1);
  return (
    <Pagination
      showControls
      variant="bordered"
      size="sm"
      page={page}
      total={10}
      onChange={setPage}
    />
  );
};
