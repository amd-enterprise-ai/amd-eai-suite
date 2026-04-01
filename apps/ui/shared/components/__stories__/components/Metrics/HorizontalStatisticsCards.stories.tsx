// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import {
  HorizontalStatisticsCards,
  type StatisticsCardProps,
} from '../../../src/Metrics/StatisticsCard';

const simpleCards: StatisticsCardProps[] = [
  { title: 'Total Clusters', tooltip: 'Number of clusters.', statistic: 12 },
  { title: 'Total Nodes', tooltip: 'Number of nodes.', statistic: 48 },
  { title: 'Available GPUs', tooltip: 'GPUs not allocated.', statistic: 32 },
  { title: 'Active Workloads', tooltip: 'Running workloads.', statistic: 5 },
];

export default {
  title: 'Components/Metrics/Horizontal Statistics Cards',
} satisfies StoryDefault;

export const Default: Story = () => (
  <div className="w-full max-w-[1250px] p-4">
    <HorizontalStatisticsCards cards={simpleCards} />
  </div>
);

export const Loading: Story = () => (
  <div className="w-full max-w-[1250px] p-4">
    <HorizontalStatisticsCards cards={simpleCards} isLoading />
  </div>
);

export const TwoCards: Story = () => (
  <div className="w-full max-w-[1250px] p-4">
    <HorizontalStatisticsCards
      cards={[
        { title: 'Clusters', tooltip: 'Total clusters.', statistic: 5 },
        { title: 'Nodes', tooltip: 'Total nodes.', statistic: 20 },
      ]}
    />
  </div>
);

const noDataCards: StatisticsCardProps[] = [
  { title: 'Total Clusters', tooltip: 'Number of clusters.' },
  { title: 'Total Nodes', tooltip: 'Number of nodes.' },
  { title: 'Available GPUs', tooltip: 'GPUs not allocated.' },
  { title: 'Active Workloads', tooltip: 'Running workloads.' },
];

export const WithNoData: Story = () => (
  <div className="w-full max-w-[1250px] p-4">
    <HorizontalStatisticsCards cards={noDataCards} />
  </div>
);
