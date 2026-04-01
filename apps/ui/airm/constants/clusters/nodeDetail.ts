// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { AvailableChartColorsKeys } from '@amdenterpriseai/types';
import {
  GpuUtilizationTabId,
  PcieTrafficTabId,
  GpuTemperatureTabId,
} from '@/types/enums/clusters';

export const ALL_DEVICES_KEY = 'all';

export const GPU_UTILIZATION_TAB_IDS: GpuUtilizationTabId[] = [
  GpuUtilizationTabId.Memory,
  GpuUtilizationTabId.Clock,
  GpuUtilizationTabId.GpuUsage,
];

export const PCIE_TRAFFIC_TAB_IDS: PcieTrafficTabId[] = [
  PcieTrafficTabId.Bandwidth,
  PcieTrafficTabId.Performance,
];

export const GPU_TEMPERATURE_TAB_IDS: GpuTemperatureTabId[] = [
  GpuTemperatureTabId.Junction,
  GpuTemperatureTabId.Memory,
];

export const CLOCK_SPEED_TICK_COUNT = 6;

export const GPU_LINE_CHART_COLORS: AvailableChartColorsKeys[] = [
  'blue',
  'emerald',
  'violet',
  'amber',
  'gray',
  'cyan',
  'pink',
  'lime',
  'fuchsia',
  'red',
  'green',
  'darkgray',
];

export const GPU_BAR_CHART_COLORS: AvailableChartColorsKeys[] =
  GPU_LINE_CHART_COLORS;

export const MAX_POWER_USAGE_INTERVALS = 12;
export const MAX_TEMPERATURE_INTERVALS = 12;
