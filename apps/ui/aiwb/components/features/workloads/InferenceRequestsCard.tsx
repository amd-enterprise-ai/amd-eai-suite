// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { TimeRangePeriod } from '@amdenterpriseai/types';
import { useMemo } from 'react';
import {
  getTickGap,
  getCurrentTimeRange,
  transformTimeSeriesDataToChartData,
} from '@amdenterpriseai/utils/app';
import { Card, CardBody, CardHeader, Tooltip } from '@heroui/react';
import { IconInfoCircle } from '@tabler/icons-react';
import { BarChart } from '@amdenterpriseai/components';
import { TimeSeriesResponse } from '@amdenterpriseai/types';
import { getInferenceRequests } from '@/lib/app/metrics';
import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/contexts/ProjectContext';
import { InferenceMetricsColors } from '@amdenterpriseai/types';

interface Props {
  namespace: string;
  workloadId: string;
  timePeriod: TimeRangePeriod;
}

const WAITING_REQUESTS_COLOR = InferenceMetricsColors.WAITING_REQUESTS;
const RUNNING_REQUESTS_COLOR = InferenceMetricsColors.RUNNING_REQUESTS;

export const InferenceRequestsCard: React.FC<Props> = ({
  namespace,
  workloadId,
  timePeriod,
}) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();

  const { data: inferenceRequestsData, isLoading: isInferenceRequestsLoading } =
    useQuery<TimeSeriesResponse>({
      queryKey: [
        'project',
        activeProject,
        'workload',
        workloadId,
        'metrics',
        'inferenceRequests',
        timePeriod,
      ],
      queryFn: () => {
        const { start, end } = getCurrentTimeRange(timePeriod);
        return getInferenceRequests({
          workloadId,
          namespace,
          start,
          end,
        });
      },
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
      className="max-w-full w-full"
      classNames={{
        base: 'shadow-sm border-1 border-default-200 rounded-sm dark:bg-default-100 overflow-visible',
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
          tickGap={getTickGap(timePeriod)}
        />
      </CardBody>
    </Card>
  );
};

export default InferenceRequestsCard;
