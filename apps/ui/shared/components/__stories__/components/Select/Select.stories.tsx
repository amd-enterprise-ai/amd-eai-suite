// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';
import type { Selection } from '../../../src/Select';
import { Select, SelectItem } from '../../../src/Select';

export default { title: 'Components/Select' } satisfies StoryDefault;

const options = [
  { key: 'apple', label: 'Apple' },
  { key: 'banana', label: 'Banana' },
];

export const SingleFlat: Story = () => {
  const [selected, setSelected] = useState<Selection>(new Set(['apple']));
  return (
    <div className="w-64 p-4">
      <Select
        label="Fruit"
        selectedKeys={selected}
        onSelectionChange={setSelected}
      >
        {options.map((o) => (
          <SelectItem key={o.key}>{o.label}</SelectItem>
        ))}
      </Select>
    </div>
  );
};

export const SingleCompound: Story = () => {
  const [selected, setSelected] = useState<Selection>(new Set(['banana']));
  return (
    <div className="w-64 p-4">
      <Select
        label="Fruit"
        selectedKeys={selected}
        onSelectionChange={setSelected}
      >
        {options.map((o) => (
          <Select.Item key={o.key}>{o.label}</Select.Item>
        ))}
      </Select>
    </div>
  );
};

export const Multiple: Story = () => {
  const [selected, setSelected] = useState<Selection>(
    new Set(['apple', 'banana']),
  );
  return (
    <div className="w-64 p-4">
      <Select
        label="Fruits"
        selectionMode="multiple"
        selectedKeys={selected}
        onSelectionChange={setSelected}
      >
        {options.map((o) => (
          <SelectItem key={o.key}>{o.label}</SelectItem>
        ))}
      </Select>
    </div>
  );
};
