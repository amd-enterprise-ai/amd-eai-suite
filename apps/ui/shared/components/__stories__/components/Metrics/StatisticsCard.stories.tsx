// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { StatisticsCard } from '../../../src/Metrics/StatisticsCard';

export default {
  title: 'Components/Metrics/Statistics Card',
} satisfies StoryDefault;

export const Default: Story = () => (
  <div className="w-full max-w-sm p-4">
    <StatisticsCard
      title="GPU Count"
      tooltip="Total number of GPUs available on this node."
      statistic={8}
    />
  </div>
);

export const WithUpperLimit: Story = () => (
  <div className="w-full max-w-sm p-4">
    <StatisticsCard
      title="CPU Cores"
      tooltip="Number of CPU cores (upper limit shown for quota context)."
      statistic={32}
      upperLimit={64}
    />
  </div>
);

export const NoData: Story = () => (
  <div className="w-full max-w-sm p-4">
    <StatisticsCard
      title="GPU Memory"
      tooltip="Total GPU memory in bytes (human-readable when present)."
    />
  </div>
);

export const Loading: Story = () => (
  <div className="w-full max-w-sm p-4">
    <StatisticsCard
      title="System Memory"
      tooltip="System RAM in bytes."
      statistic={68719476736}
      upperLimit={137438953472}
      isLoading
    />
  </div>
);

export const Compact: Story = () => (
  <div className="w-full max-w-sm p-4">
    <StatisticsCard
      title="GPU Type"
      tooltip="Model name of the GPU(s)."
      statistic={0}
      compact
      statisticFormatter={() => 'Instinct M1350'}
    />
  </div>
);

export const CustomFormatter: Story = () => (
  <div className="w-full max-w-sm p-4">
    <StatisticsCard
      title="GPU Memory"
      tooltip="Total GPU memory (formatted as human-readable)."
      statistic={2199023255552}
      statisticFormatter={(val) =>
        val >= 1e12
          ? `${(val / 1e12).toFixed(2)} TB`
          : `${(val / 1e9).toFixed(2)} GB`
      }
    />
  </div>
);

export const AllStates: Story = () => (
  <div className="flex flex-wrap gap-4 p-4">
    <div className="w-64">
      <StatisticsCard title="GPU Count" tooltip="Total GPUs." statistic={8} />
    </div>
    <div className="w-64">
      <StatisticsCard
        title="CPU Cores"
        tooltip="CPU cores with limit."
        statistic={32}
        upperLimit={64}
      />
    </div>
    <div className="w-64">
      <StatisticsCard title="No Data" tooltip="Shows no-data state." />
    </div>
    <div className="w-64">
      <StatisticsCard
        title="Loading"
        tooltip="Skeleton state."
        statistic={100}
        isLoading
      />
    </div>
    <div className="w-64">
      <StatisticsCard
        title="Compact"
        tooltip="Compact layout."
        statistic={0}
        compact
        statisticFormatter={() => 'M1350'}
      />
    </div>
  </div>
);
