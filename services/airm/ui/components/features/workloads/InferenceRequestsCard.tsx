// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { TimeRangePeriod } from '@/types/enums/metrics';
import { useMemo } from 'react';
import {
  getTickGap,
  transformTimeSeriesDataToChartData,
} from '@/utils/app/charts';
import { Card, CardBody, CardHeader, Tooltip } from '@heroui/react';
import { IconInfoCircle } from '@tabler/icons-react';
import { BarChart } from '@/components/shared/Metrics/BarChart';
import { Workload } from '@/types/workloads';
import { TimeRange, TimeSeriesResponse } from '@/types/metrics';
import { getInferenceRequests } from '@/services/app/workloads';
import { WorkloadType, WorkloadStatus } from '@/types/enums/workloads';
import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/contexts/ProjectContext';
import { InferenceMetricsColors } from '@/types/enums/inference-metrics';

interface Props {
  workload: Workload;
  timeRange: TimeRange;
  timeRangePeriod: TimeRangePeriod;
  width?: number;
}

const WAITING_REQUESTS_COLOR = InferenceMetricsColors.WAITING_REQUESTS;
const RUNNING_REQUESTS_COLOR = InferenceMetricsColors.RUNNING_REQUESTS;

export const InferenceRequestsCard: React.FC<Props> = ({
  workload,
  timeRange,
  timeRangePeriod,
  width = 600,
}) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();

  const { data: inferenceRequestsData, isLoading: isInferenceRequestsLoading } =
    useQuery<TimeSeriesResponse>({
      queryKey: [
        'project',
        activeProject,
        'workload',
        workload.id,
        'metrics',
        'inferenceRequests',
        {
          start: timeRange.start.toISOString(),
          end: timeRange.end.toISOString(),
        },
      ],
      queryFn: () =>
        getInferenceRequests(
          workload.id as string,
          timeRange.start,
          timeRange.end,
        ),
      enabled:
        !!workload.id &&
        workload?.type === WorkloadType.INFERENCE &&
        workload?.status === WorkloadStatus.RUNNING,
    });

  const inferenceRequestsChartData = useMemo(() => {
    if (!inferenceRequestsData?.data) return null;

    const mappedData = inferenceRequestsData.data.map((item) => ({
      ...item,
      metadata: {
        ...item.metadata,
        metric: item.metadata.label,
      },
    }));

    return transformTimeSeriesDataToChartData(
      mappedData,
      inferenceRequestsData.range.timestamps,
      'metric',
    );
  }, [inferenceRequestsData]);

  return (
    <Card
      className={`max-w-full xl:max-w-[${width}px]`}
      classNames={{
        base: 'shadow-sm border-1 border-default-200 rounded-sm	dark:bg-default-100 overflow-visible',
      }}
    >
      <CardHeader>
        <div className="flex items-center flex-grow">
          <div>{t('details.metrics.inferenceRequests.title')}</div>
          <div className="ml-auto">
            <Tooltip
              content={t('details.metrics.inferenceRequests.description')}
              className="max-w-[300px]"
            >
              <IconInfoCircle
                className="text-default-400 cursor-pointer"
                size={16}
              />
            </Tooltip>
          </div>
        </div>
      </CardHeader>
      <CardBody className="overflow-visible pt-2">
        <BarChart
          type="stacked"
          data={
            inferenceRequestsChartData ? inferenceRequestsChartData.data : []
          }
          categories={
            inferenceRequestsChartData
              ? inferenceRequestsChartData.categories
              : []
          }
          colors={[RUNNING_REQUESTS_COLOR, WAITING_REQUESTS_COLOR]}
          isLoading={isInferenceRequestsLoading}
          index="date"
          tickGap={getTickGap(timeRangePeriod)}
        />
      </CardBody>
    </Card>
  );
};

export default InferenceRequestsCard;
