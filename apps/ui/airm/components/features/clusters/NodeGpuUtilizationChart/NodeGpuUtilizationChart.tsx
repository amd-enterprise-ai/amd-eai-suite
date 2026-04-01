// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useState } from 'react';

import type { AvailableChartColorsKeys } from '@amdenterpriseai/types';

import { DynamicValueLegend } from '@amdenterpriseai/components';
import { LineChart } from '@amdenterpriseai/components';

interface Props {
  data: Record<string, string | number | null>[];
  categories: string[];
  colors: AvailableChartColorsKeys[];
  isLoading: boolean;
  showNoData: boolean;
  noDataMessage: string;
  loadingText: string;
  unit?: string;
  valueFormatter?: (value: number) => string;
  minValue?: number;
  maxValue?: number;
  yAxisTickCount?: number;
  yAxisWidth?: number;
  marginTop?: number;
}

const defaultValueFormatter = (v: number) => `${Number(v).toFixed(0)}%`;

export const NodeGpuUtilizationChart: React.FC<Props> = ({
  data,
  categories,
  colors,
  isLoading,
  showNoData,
  noDataMessage,
  loadingText,
  unit = '%',
  yAxisTickCount,
  yAxisWidth = 64,
  marginTop,
  valueFormatter = defaultValueFormatter,
  minValue = 0,
  maxValue = 100,
}) => {
  const [hoveredChartPoint, setHoveredChartPoint] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [activeLegendGpu, setActiveLegendGpu] = useState<string | undefined>(
    undefined,
  );

  const isBandwidthChart = unit === '';
  const lineChartMaxValue = isBandwidthChart ? undefined : (maxValue ?? 100);

  if (showNoData) {
    return <p className="text-default-500 text-sm">{noDataMessage}</p>;
  }

  return (
    <>
      <LineChart
        data={data}
        index="date"
        categories={categories}
        colors={colors}
        valueFormatter={valueFormatter}
        minValue={minValue}
        yAxisTickCount={yAxisTickCount}
        marginTop={marginTop}
        maxValue={lineChartMaxValue}
        showLegend={false}
        showYAxis={true}
        connectNulls={true}
        className="h-72"
        yAxisWidth={yAxisWidth}
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
          unit={unit}
          isLoading={isLoading}
          valueFormatter={valueFormatter}
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
