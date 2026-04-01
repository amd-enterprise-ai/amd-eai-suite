// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useState } from 'react';

import type { AvailableChartColorsKeys } from '@amdenterpriseai/types';

import { BarChart } from '@amdenterpriseai/components';
import { DynamicValueLegend } from '@amdenterpriseai/components';

interface Props {
  data: Record<string, string | number | null>[];
  categories: string[];
  colors: AvailableChartColorsKeys[];
  isLoading: boolean;
  showNoData: boolean;
  noDataMessage: string;
  loadingText: string;
}

const temperatureFormatter = (v: number) =>
  `${Number.isInteger(v) ? v : Number(v).toFixed(1)}\u00B0C`;

export const NodeGpuTemperatureChart: React.FC<Props> = ({
  data,
  categories,
  colors,
  isLoading,
  showNoData,
  noDataMessage,
  loadingText,
}) => {
  const [hoveredChartPoint, setHoveredChartPoint] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [activeLegendGpu, setActiveLegendGpu] = useState<string | undefined>(
    undefined,
  );

  if (showNoData) {
    return <p className="text-default-500 text-sm">{noDataMessage}</p>;
  }

  return (
    <>
      <BarChart
        data={data}
        index="date"
        categories={categories}
        colors={colors}
        valueFormatter={temperatureFormatter}
        minValue={0}
        maxValue={100}
        allowDecimals={false}
        showLegend={false}
        showYAxis={true}
        className="h-72"
        activeLegendProp={activeLegendGpu}
        tooltipCallback={({ active, payload }) => {
          setHoveredChartPoint(
            active && payload?.length
              ? (payload[0].payload as Record<string, unknown>)
              : null,
          );
        }}
        isLoading={isLoading}
        loadingText={loadingText}
      />
      {(isLoading || categories.length > 0) && (
        <DynamicValueLegend
          categories={categories}
          colors={colors}
          data={data as Record<string, unknown>[]}
          unit={'\u00B0C'}
          isLoading={isLoading}
          valueFormatter={temperatureFormatter}
          displayPoint={hoveredChartPoint}
          activeCategory={activeLegendGpu}
          onCategoryClick={(category) =>
            setActiveLegendGpu((prev) =>
              prev === category ? undefined : category,
            )
          }
        />
      )}
    </>
  );
};
