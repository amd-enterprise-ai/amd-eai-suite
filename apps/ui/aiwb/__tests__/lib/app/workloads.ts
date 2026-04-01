// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { transformTimeSeriesDataToChartData } from '@/lib/app/workloads';

describe('transformTimeSeriesDataToChartData', () => {
  it('should transform time series data into chart data', () => {
    const mockTimeStamp1 = new Date();
    const mockTimeStamp2 = new Date(mockTimeStamp1.getTime() + 15 * 60 * 1000);
    const input = [
      {
        metadata: { category: { id: '1', name: 'Category 1' } },
        values: [
          { timestamp: mockTimeStamp1.toISOString(), value: 10 },
          { timestamp: mockTimeStamp2.toISOString(), value: 20 },
        ],
      },
      {
        metadata: { category: { id: '2', name: 'Category 2' } },
        values: [
          { timestamp: mockTimeStamp1.toISOString(), value: 30 },
          { timestamp: mockTimeStamp2.toISOString(), value: 40 },
        ],
      },
    ];
    const timestamps = [
      mockTimeStamp1.toISOString(),
      mockTimeStamp2.toISOString(),
    ];

    const result = transformTimeSeriesDataToChartData(
      input,
      timestamps,
      'category',
    );
    expect(result.data).toEqual([
      {
        date: mockTimeStamp1.toISOString(),
        'Category 1': 10,
        'Category 2': 30,
      },
      {
        date: mockTimeStamp2.toISOString(),
        'Category 1': 20,
        'Category 2': 40,
      },
    ]);
    expect(result.categories).toEqual(['Category 1', 'Category 2']);
  });
});
