// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';

import { Tab, Tabs } from '../../../src/Tabs';

export default {
  title: 'Components/Tabs',
} satisfies StoryDefault;

export const FlatImports: Story = () => {
  const [selectedKey, setSelectedKey] = useState('overview');

  return (
    <div className="w-full max-w-lg p-4">
      <Tabs selectedKey={selectedKey} onSelectionChange={setSelectedKey}>
        <Tab key="overview" title="Overview">
          <p className="p-4 text-sm">Overview content (flat Tab import).</p>
        </Tab>
        <Tab key="details" title="Details">
          <p className="p-4 text-sm">Details content (flat Tab import).</p>
        </Tab>
      </Tabs>
    </div>
  );
};

export const CompoundSyntax: Story = () => {
  const [selectedKey, setSelectedKey] = useState('metrics');

  return (
    <div className="w-full max-w-lg p-4">
      <Tabs selectedKey={selectedKey} onSelectionChange={setSelectedKey}>
        <Tabs.Tab key="metrics" title="Metrics">
          <p className="p-4 text-sm">Metrics panel (Tabs.Tab compound).</p>
        </Tabs.Tab>
        <Tabs.Tab key="logs" title="Logs">
          <p className="p-4 text-sm">Logs panel (Tabs.Tab compound).</p>
        </Tabs.Tab>
      </Tabs>
    </div>
  );
};
