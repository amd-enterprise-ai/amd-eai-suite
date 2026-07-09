// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';
import type { Selection } from '../../../src/Select';
import { Listbox, ListboxItem, ListboxSection } from '../../../src/Listbox';

export default { title: 'Components/Listbox' } satisfies StoryDefault;

const options = [
  { key: 'apple', label: 'Apple' },
  { key: 'banana', label: 'Banana' },
];

export const Flat: Story = () => {
  const [selected, setSelected] = useState<Selection>(new Set(['apple']));
  return (
    <div className="w-64 p-4">
      <Listbox
        aria-label="Fruit"
        selectedKeys={selected}
        onSelectionChange={setSelected}
      >
        {options.map((o) => (
          <ListboxItem key={o.key}>{o.label}</ListboxItem>
        ))}
      </Listbox>
    </div>
  );
};

export const Compound: Story = () => {
  const [selected, setSelected] = useState<Selection>(new Set(['banana']));
  return (
    <div className="w-64 p-4">
      <Listbox
        aria-label="Fruit"
        selectedKeys={selected}
        onSelectionChange={setSelected}
      >
        <Listbox.Section title="Popular">
          {options.map((o) => (
            <Listbox.Item key={o.key}>{o.label}</Listbox.Item>
          ))}
        </Listbox.Section>
      </Listbox>
    </div>
  );
};

export const WithSectionDivider: Story = () => {
  const [selected, setSelected] = useState<Selection>(new Set(['add']));
  return (
    <div className="w-64 p-4">
      <Listbox
        aria-label="Tokens"
        selectedKeys={selected}
        onSelectionChange={setSelected}
      >
        <ListboxSection showDivider title="Existing">
          <ListboxItem key="token-a">Token A</ListboxItem>
        </ListboxSection>
        <ListboxItem key="add">Add new</ListboxItem>
      </Listbox>
    </div>
  );
};
