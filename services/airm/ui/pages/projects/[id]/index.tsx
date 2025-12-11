// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { IconSettings } from '@tabler/icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useRouter } from 'next/router';

import {
  fetchProjectAverageGPUIdleTime,
  fetchProjectAverageWaitTime,
  fetchProjectGPUDeviceUtilization,
  fetchProjectGPUMemoryUtilization,
  fetchProjectWorkloadsStatuses,
} from '@/services/app/projects';
import { getProject } from '@/services/server/projects';

import { getLatestDate } from '@/utils/app/date';
import { getProjectEditUrl } from '@/utils/app/projects';
import { getCurrentTimeRange } from '@/utils/app/time-range';
import { authOptions } from '@/utils/server/auth';

import { TimeRangePeriod } from '@/types/enums/metrics';
import {
  MetricScalarResponse,
  ProjectWorkloadsStatusesResponse,
  TimeRange,
  TimeSeriesAllocationData,
  TimeSeriesResponse,
} from '@/types/metrics';
import { ProjectWithMembers } from '@/types/projects';

import {
  AverageGPUIdleTimeCard,
  AverageWaitTimeCard,
  GPUDeviceUsageCard,
  GPUMemoryUsageCard,
  ProjectWorkloadsStatsCard,
  ProjectWorkloadsTable,
  QuotaUtilizationCard,
} from '@/components/features/projects';
import { ActionButton } from '@/components/shared/Buttons';
import { ChartTimeSelector } from '@/components/shared/Metrics/ChartTimeSelector';

import { isEqual } from 'lodash';

const GPU_MEMORY_UTILIZATION_NUMERATOR_LABEL = 'utilized_gpu_vram';
const GPU_MEMORY_UTILIZATION_DENOMINATOR_LABEL = 'allocated_gpu_vram';
const GPU_DEVICE_UTILIZATION_NUMERATOR_LABEL = 'utilized_gpus';
const GPU_DEVICE_UTILIZATION_DENOMINATOR_LABEL = 'allocated_gpus';

interface Props {
  project: ProjectWithMembers;
}

const ProjectDashboardPage: React.FC<Props> = ({ project }) => {
  const { t } = useTranslation('projects');
  const router = useRouter();
  const { id } = router.query;
  const queryClient = useQueryClient();

  const [timeRange, setTimeRange] = useState<TimeRange>(
    getCurrentTimeRange(TimeRangePeriod['1H']),
  );
  const currentTimePeriod = useRef<TimeRangePeriod>(TimeRangePeriod['1H']);

  const {
    data: projectWorkloadsStatuses,
    isLoading: isProjectWorkloadsStatusesLoading,
  } = useQuery<ProjectWorkloadsStatusesResponse>({
    queryKey: ['project', 'metrics', 'statuses', id],
    queryFn: () => fetchProjectWorkloadsStatuses(id as string),
  });

  const {
    data: projectGPUMemoryUtilization,
    isLoading: isProjectGPUMemoryUtilizationLoading,
    dataUpdatedAt: projectGPUMemoryUtilizationUpdatedAt,
  } = useQuery<TimeSeriesResponse>({
    queryKey: [
      'project',
      'metrics',
      'gpu-memory-utilization',
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchProjectGPUMemoryUtilization(
        id as string,
        timeRange.start,
        timeRange.end,
      );
    },
  });

  const {
    data: projectGPUDeviceUtilization,
    isLoading: isProjectGPUDeviceUtilizationLoading,
    dataUpdatedAt: projectGPUDeviceUtilizationUpdatedAt,
  } = useQuery<TimeSeriesResponse>({
    queryKey: [
      'project',
      'metrics',
      'gpu-device-utilization',
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchProjectGPUDeviceUtilization(
        id as string,
        timeRange.start,
        timeRange.end,
      );
    },
  });

  const {
    data: projectAverageWaitTime,
    isLoading: isProjectAverageWaitTimeLoading,
    dataUpdatedAt: projectAverageWaitTimeUpdatedAt,
  } = useQuery<MetricScalarResponse>({
    queryKey: [
      'project',
      'metrics',
      'average-wait-time',
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchProjectAverageWaitTime(
        id as string,
        timeRange.start,
        timeRange.end,
      );
    },
  });

  const {
    data: projectAverageGPUIdleTime,
    isLoading: isProjectAverageGPUIdleTimeLoading,
    dataUpdatedAt: projectAverageGPUIdleTimeUpdatedAt,
  } = useQuery<MetricScalarResponse>({
    queryKey: [
      'project',
      'metrics',
      'gpu-idle-time',
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchProjectAverageGPUIdleTime(
        id as string,
        timeRange.start,
        timeRange.end,
      );
    },
  });

  const projectGPUMemoryUtilizationChartData: TimeSeriesAllocationData =
    useMemo(() => {
      if (!projectGPUMemoryUtilization?.data)
        return { numerator: [], denominator: [] };
      const utilized = projectGPUMemoryUtilization.data.find(
        (s) => s.metadata?.label === GPU_MEMORY_UTILIZATION_NUMERATOR_LABEL,
      );
      const allocated = projectGPUMemoryUtilization.data.find(
        (s) => s.metadata?.label === GPU_MEMORY_UTILIZATION_DENOMINATOR_LABEL,
      );
      return {
        numerator: utilized?.values ?? [],
        denominator: allocated?.values ?? [],
      };
    }, [projectGPUMemoryUtilization]);

  const projectGPUDeviceUtilizationChartData: TimeSeriesAllocationData =
    useMemo(() => {
      if (!projectGPUDeviceUtilization?.data)
        return { numerator: [], denominator: [] };
      const utilized = projectGPUDeviceUtilization.data.find(
        (s) => s.metadata?.label === GPU_DEVICE_UTILIZATION_NUMERATOR_LABEL,
      );
      const allocated = projectGPUDeviceUtilization.data.find(
        (s) => s.metadata?.label === GPU_DEVICE_UTILIZATION_DENOMINATOR_LABEL,
      );
      return {
        numerator: utilized?.values ?? [],
        denominator: allocated?.values ?? [],
      };
    }, [projectGPUDeviceUtilization]);

  const handleTimeBoundChange = useCallback(
    (timePeriod: TimeRangePeriod, timeRange: TimeRange) => {
      currentTimePeriod.current = timePeriod as TimeRangePeriod;
      setTimeRange(timeRange);
    },
    [setTimeRange, currentTimePeriod],
  );

  const handleChartsRefresh = useCallback(() => {
    const newRange = getCurrentTimeRange(currentTimePeriod.current);
    if (isEqual(newRange, timeRange)) {
      queryClient.invalidateQueries({
        queryKey: ['project', 'metrics'],
      });
    } else {
      // Time range has changed, set the new time range and react-query will auto refetch the data
      setTimeRange(newRange);
    }
  }, [timeRange, queryClient]);

  const isMetricsLoading = useMemo(() => {
    return (
      isProjectGPUDeviceUtilizationLoading ||
      isProjectGPUMemoryUtilizationLoading ||
      isProjectAverageWaitTimeLoading ||
      isProjectAverageGPUIdleTimeLoading
    );
  }, [
    isProjectGPUDeviceUtilizationLoading,
    isProjectGPUMemoryUtilizationLoading,
    isProjectAverageWaitTimeLoading,
    isProjectAverageGPUIdleTimeLoading,
  ]);

  const dataLastUpdatedAt = useMemo(() => {
    const latestTimestamps: Date[] = [];

    if (projectGPUDeviceUtilizationUpdatedAt) {
      latestTimestamps.push(new Date(projectGPUDeviceUtilizationUpdatedAt));
    }
    if (projectGPUMemoryUtilizationUpdatedAt) {
      latestTimestamps.push(new Date(projectGPUMemoryUtilizationUpdatedAt));
    }
    if (projectAverageWaitTimeUpdatedAt) {
      latestTimestamps.push(new Date(projectAverageWaitTimeUpdatedAt));
    }
    if (projectAverageGPUIdleTimeUpdatedAt) {
      latestTimestamps.push(new Date(projectAverageGPUIdleTimeUpdatedAt));
    }
    return getLatestDate(latestTimestamps);
  }, [
    projectGPUDeviceUtilizationUpdatedAt,
    projectGPUMemoryUtilizationUpdatedAt,
    projectAverageWaitTimeUpdatedAt,
    projectAverageGPUIdleTimeUpdatedAt,
  ]);

  return (
    <div className="flex flex-col gap-8 mt-8">
      <div className="flex flex-col justify-center">
        <div className="mb-8 flex items-center justify-between">
          <h3>{t('dashboard.overview.title')}</h3>
          <div className="flex items-center gap-3">
            <ChartTimeSelector
              onTimeRangeChange={handleTimeBoundChange}
              initialTimePeriod={TimeRangePeriod['1H']}
              translationPrefix="timeRange"
              onChartsRefresh={handleChartsRefresh}
              isFetching={isMetricsLoading}
              lastFetchedTimestamp={dataLastUpdatedAt}
            />
            <ActionButton
              onPress={() => {
                router.push(getProjectEditUrl(id as string));
              }}
              icon={<IconSettings size={16} stroke={2} />}
            >
              {t('dashboard.action.projectSettings')}
            </ActionButton>
          </div>
        </div>
        <div className="flex justify-center grow">
          <div className="grid w-full max-w-[1800px] gap-4 grid-cols-1 md:grid-cols-3">
            <div className="md:row-span-2 flex justify-end">
              <ProjectWorkloadsStatsCard
                isLoading={isProjectWorkloadsStatusesLoading}
                projectName={project.name}
                totalWorkloads={projectWorkloadsStatuses?.totalWorkloads ?? 0}
                data={projectWorkloadsStatuses?.statusCounts ?? []}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:col-span-2">
              <AverageWaitTimeCard
                data={projectAverageWaitTime}
                isLoading={isProjectAverageWaitTimeLoading}
              />
              <QuotaUtilizationCard
                data={projectGPUDeviceUtilizationChartData}
                isLoading={isProjectGPUDeviceUtilizationLoading}
              />
              <AverageGPUIdleTimeCard
                data={projectAverageGPUIdleTime}
                isLoading={isProjectAverageGPUIdleTimeLoading}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:col-span-2">
              <GPUDeviceUsageCard
                data={projectGPUDeviceUtilizationChartData}
                isLoading={isProjectGPUDeviceUtilizationLoading}
              />
              <GPUMemoryUsageCard
                data={projectGPUMemoryUtilizationChartData}
                isLoading={isProjectGPUMemoryUtilizationLoading}
              />
            </div>
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-8">
        <h3>{t('dashboard.workloads.title')}</h3>
        <ProjectWorkloadsTable projectId={id as string} />
      </div>
    </div>
  );
};

export default ProjectDashboardPage;

export async function getServerSideProps(context: any) {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  try {
    const project = await getProject(
      context.params.id,
      session?.accessToken as string,
    );

    const translations = await serverSideTranslations(locale, [
      'common',
      'projects',
      'users',
      'workloads',
    ]);

    const breadcrumb = [
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.projects?.title,
        href: '/projects',
      },
      {
        title: `${project.name}`,
        href: `/projects/${project.id}`,
      },
    ];

    return {
      props: {
        ...translations,
        project,
        pageBreadcrumb: breadcrumb,
      },
    };
  } catch (error) {
    console.error('Project not found: ' + error);
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }
}
