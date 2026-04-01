// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';

import { Skeleton } from '@heroui/react';

import {
  chartColors,
  type AvailableChartColorsKeys,
} from '@amdenterpriseai/types';
import type { ColorUtility } from '@amdenterpriseai/types';

const DEFAULT_LOADING_ITEM_COUNT = 8;

function getColorClassName(
  color: AvailableChartColorsKeys,
  type: ColorUtility,
): string {
  return chartColors[color]?.[type] ?? 'bg-gray-500';
}

export interface DynamicValueLegendProps {
  categories: string[];
  colors: AvailableChartColorsKeys[];
  data: Record<string, unknown>[];
  unit: string;
  isLoading?: boolean;
  loadingItemCount?: number;
  valueFormatter?: (value: number) => string;
  /** When set (e.g. from tooltip hover), legend shows values at this point; otherwise last data point. */
  displayPoint?: Record<string, unknown> | null;
  activeCategory?: string;
  onCategoryClick?: (category: string) => void;
}

export const DynamicValueLegend: React.FC<DynamicValueLegendProps> = ({
  categories,
  colors,
  data,
  unit,
  isLoading = false,
  loadingItemCount = DEFAULT_LOADING_ITEM_COUNT,
  valueFormatter,
  displayPoint,
  activeCategory,
  onCategoryClick,
}) => {
  const point = displayPoint ?? data[data.length - 1];
  return (
    <div
      className="grid gap-2 mt-3"
      style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))' }}
    >
      {isLoading
        ? Array.from({ length: loadingItemCount }, (_, i) => (
            <div
              key={i}
              className="flex flex-col gap-0.5 rounded-md border border-gray-200 dark:border-gray-700 px-3 py-2"
            >
              <div className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-sm shrink-0 bg-gray-300 dark:bg-gray-600 animate-pulse" />
                <Skeleton className="h-3 w-12 rounded" />
              </div>
              <Skeleton className="h-4 w-10 rounded mt-0.5" />
            </div>
          ))
        : categories.map((category, idx) => {
            const value = point?.[category] as number | undefined;
            const formatted =
              value !== undefined && value !== null
                ? valueFormatter
                  ? valueFormatter(value)
                  : `${value}${unit}`
                : 'N/A';
            const isActive = activeCategory === category;
            const isDimmed = activeCategory && activeCategory !== category;
            return (
              <button
                type="button"
                key={category}
                onClick={() => onCategoryClick?.(category)}
                className={`flex flex-col gap-0.5 rounded-md border px-3 py-2 cursor-pointer transition text-left ${
                  isActive
                    ? 'border-gray-400 dark:border-gray-500 bg-gray-100 dark:bg-gray-800'
                    : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'
                } ${isDimmed ? 'opacity-40' : ''}`}
              >
                <div className="flex items-center gap-1.5">
                  <span
                    className={`size-2.5 rounded-sm shrink-0 ${getColorClassName(colors[idx], 'bg')}`}
                  />
                  <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {category}
                  </span>
                </div>
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-50 whitespace-nowrap">
                  {formatted}
                </span>
              </button>
            );
          })}
    </div>
  );
};
