// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';

import type { GetServerSidePropsContext } from 'next/types';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import {
  fetchProjectGPUDeviceUtilization,
  fetchProjectGPUMemoryUtilization,
  fetchProjectWorkloadStats,
} from '@/lib/app/projects';

import { displayHumanReadableMegaBytes } from '@amdenterpriseai/utils/app';
import { getCurrentTimeRange } from '@amdenterpriseai/utils/app';

import { TimeRangePeriod } from '@amdenterpriseai/types';
import {
  TimeRange,
  TimeSeriesAllocationData,
  TimeSeriesResponse,
} from '@amdenterpriseai/types';
import type { WorkloadStatsResponse } from '@/types/projects';

import {
  ProjectWorkloadsStatsCard,
  NamespaceWorkloadsTable,
} from '@/components/features/projects';
import {
  AiwbDocsPage,
  aiwbDocumentationMapping,
  ChartTimeSelector,
  RelevantDocs,
  StatsWithLineChart,
} from '@amdenterpriseai/components';

import { useProject } from '@/contexts/ProjectContext';
import {
  DOCS_WORKBENCH_BASE,
  WithDocumentationLink,
} from '@amdenterpriseai/utils/app';
import { useIsLoading, useLastQueryUpdated } from '@amdenterpriseai/hooks';

const GPU_MEMORY_UTILIZATION_NUMERATOR_LABEL = 'gpu_memory_utilization';
const GPU_MEMORY_UTILIZATION_DENOMINATOR_LABEL = 'allocated_gpu_vram';
const GPU_DEVICE_UTILIZATION_NUMERATOR_LABEL = 'gpu_device_utilization';
const GPU_DEVICE_UTILIZATION_DENOMINATOR_LABEL = 'allocated_gpus';

const ProjectDashboardPage: React.FC & WithDocumentationLink = () => {
  const { t } = useTranslation(['projects', 'workloads', 'models']);
  const { activeProject } = useProject();
  const queryClient = useQueryClient();

  const namespaceMetricsQueryKeyPrefix = useMemo(
    () => ['project', activeProject, 'metrics'] as readonly string[],
    [activeProject],
  );

  const [timeRange, setTimeRange] = useState<TimeRange>(
    getCurrentTimeRange(TimeRangePeriod['15M']),
  );
  const currentTimePeriod = useRef<TimeRangePeriod>(TimeRangePeriod['15M']);

  const { data: namespaceStats, isLoading: isNamespaceStatsLoading } =
    useQuery<WorkloadStatsResponse>({
      queryKey: ['project', activeProject, 'stats'],
      queryFn: () => fetchProjectWorkloadStats(activeProject as string),
      enabled: !!activeProject,
    });

  const {
    data: namespaceGPUMemoryUtilization,
    isLoading: isNamespaceGPUMemoryUtilizationLoading,
  } = useQuery<TimeSeriesResponse>({
    queryKey: [
      ...namespaceMetricsQueryKeyPrefix,
      'gpu-memory-utilization',
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchProjectGPUMemoryUtilization(
        activeProject as string,
        timeRange.start,
        timeRange.end,
      );
    },
    enabled: !!activeProject,
  });

  const {
    data: namespaceGPUDeviceUtilization,
    isLoading: isNamespaceGPUDeviceUtilizationLoading,
  } = useQuery<TimeSeriesResponse>({
    queryKey: [
      ...namespaceMetricsQueryKeyPrefix,
      'gpu-device-utilization',
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchProjectGPUDeviceUtilization(
        activeProject as string,
        timeRange.start,
        timeRange.end,
      );
    },
    enabled: !!activeProject,
  });

  const namespaceGPUMemoryUtilizationChartData: TimeSeriesAllocationData =
    useMemo(() => {
      if (!namespaceGPUMemoryUtilization?.data)
        return { numerator: [], denominator: [] };
      const utilized = namespaceGPUMemoryUtilization.data.find(
        (s) => s.metadata?.label === GPU_MEMORY_UTILIZATION_NUMERATOR_LABEL,
      );
      const allocated = namespaceGPUMemoryUtilization.data.find(
        (s) => s.metadata?.label === GPU_MEMORY_UTILIZATION_DENOMINATOR_LABEL,
      );
      return {
        numerator: utilized?.values ?? [],
        denominator: allocated?.values ?? [],
      };
    }, [namespaceGPUMemoryUtilization]);

  const namespaceGPUDeviceUtilizationChartData: TimeSeriesAllocationData =
    useMemo(() => {
      if (!namespaceGPUDeviceUtilization?.data)
        return { numerator: [], denominator: [] };
      const utilized = namespaceGPUDeviceUtilization.data.find(
        (s) => s.metadata?.label === GPU_DEVICE_UTILIZATION_NUMERATOR_LABEL,
      );
      const allocated = namespaceGPUDeviceUtilization.data.find(
        (s) => s.metadata?.label === GPU_DEVICE_UTILIZATION_DENOMINATOR_LABEL,
      );
      return {
        numerator: utilized?.values ?? [],
        denominator: allocated?.values ?? [],
      };
    }, [namespaceGPUDeviceUtilization]);

  const handleTimeBoundChange = useCallback(
    (timePeriod: TimeRangePeriod, timeRange: TimeRange) => {
      currentTimePeriod.current = timePeriod as TimeRangePeriod;
      setTimeRange(timeRange);
    },
    [setTimeRange, currentTimePeriod],
  );

  const handleRefresh = useCallback(() => {
    setTimeRange(getCurrentTimeRange(currentTimePeriod.current));
    queryClient.invalidateQueries({
      queryKey: ['project', activeProject, 'workloads'],
    });
    queryClient.resetQueries({
      queryKey: ['project', activeProject, 'stats'],
    });
  }, [queryClient, activeProject]);

  const isMetricsLoading = useIsLoading(namespaceMetricsQueryKeyPrefix);

  const dataLastUpdatedAt = useLastQueryUpdated(namespaceMetricsQueryKeyPrefix);

  return (
    <div className="min-h-full flex flex-col">
      <div className="flex-1 flex flex-col gap-8 mt-8">
        <div className="flex flex-col justify-center">
          <div className="mb-8 flex items-center justify-between">
            <h3>{t('dashboard.overview.title')}</h3>
            <ChartTimeSelector
              onTimeRangeChange={handleTimeBoundChange}
              initialTimePeriod={TimeRangePeriod['15M']}
              translationPrefix="timeRange"
              onChartsRefresh={handleRefresh}
              isFetching={isMetricsLoading}
              lastFetchedTimestamp={dataLastUpdatedAt}
              periods={[
                TimeRangePeriod['15M'],
                TimeRangePeriod['30M'],
                TimeRangePeriod['1H'],
                TimeRangePeriod['24H'],
                TimeRangePeriod['7D'],
              ]}
            />
          </div>
          <div className="flex justify-center grow">
            <div className="grid w-full max-w-[1800px] gap-4 grid-cols-1 min-[1100px]:grid-cols-3">
              <div className="flex justify-end">
                <ProjectWorkloadsStatsCard
                  isLoading={isNamespaceStatsLoading}
                  projectName={activeProject ?? 'Namespace'}
                  totalWorkloads={namespaceStats?.total ?? 0}
                  data={namespaceStats?.statusCounts ?? []}
                />
              </div>
              <StatsWithLineChart
                title={t('dashboard.overview.gpuDeviceUsage.title')}
                tooltip={t('dashboard.overview.gpuDeviceUsage.description')}
                data={namespaceGPUDeviceUtilizationChartData.numerator}
                dataFormatter={(value) => Number(value).toFixed(0)}
                isLoading={isNamespaceGPUDeviceUtilizationLoading}
                fillHeight
              />
              <StatsWithLineChart
                title={t('dashboard.overview.vramDeviceUsage.title')}
                tooltip={t('dashboard.overview.vramDeviceUsage.description')}
                data={namespaceGPUMemoryUtilizationChartData.numerator}
                dataFormatter={(value) =>
                  displayHumanReadableMegaBytes(Number(value))
                }
                colors={['cyan', 'gray']}
                isLoading={isNamespaceGPUMemoryUtilizationLoading}
                fillHeight
              />
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-8">
          <h3>{t('dashboard.workloads.title')}</h3>
          <NamespaceWorkloadsTable namespace={activeProject as string} />
        </div>
      </div>
      <RelevantDocs docs={aiwbDocumentationMapping[AiwbDocsPage.DASHBOARD]} />
    </div>
  );
};

ProjectDashboardPage.documentationLink = `${DOCS_WORKBENCH_BASE}/dashboard.html`;

export default ProjectDashboardPage;

export async function getServerSideProps(context: GetServerSidePropsContext) {
  const { locale = 'en', params } = context;
  const project = params?.project as string;

  try {
    const translations = await serverSideTranslations(locale, [
      'common',
      'projects',
      'users',
      'workloads',
      'models',
      'sharedComponents',
    ]);

    const breadcrumb = [
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.common?.pages
            ?.dashboard?.title,
        href: `/${project}/`,
      },
    ];

    return {
      props: {
        ...translations,
        pageBreadcrumb: breadcrumb,
      },
    };
  } catch (error) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }
}
