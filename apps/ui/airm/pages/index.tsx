// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody, CardHeader } from '@heroui/react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import router from 'next/router';

import { fetchClusterStatistics } from '@/services/app';
import {
  fetchGPUDeviceUtilization,
  fetchGPUMemoryUtilization,
  fetchUtilization,
} from '@/services/app';
import { getClusterStats } from '@/services/server';

import {
  airmMenuItems,
  getAuthRedirect,
  getFirstAccessibleRoute,
  getTickGap,
  rollupTimeSeriesData,
  transformTimeSeriesDataToChartData,
} from '@amdenterpriseai/utils/app';
import { getLatestDate } from '@amdenterpriseai/utils/app';
import { getProjectDashboardUrl } from '@amdenterpriseai/utils/app';
import { displayFixedNumber } from '@amdenterpriseai/utils/app';
import { getCurrentTimeRange } from '@amdenterpriseai/utils/app';
import { authOptions } from '@amdenterpriseai/utils/server';

import { ClusterStatsResponse } from '@amdenterpriseai/types';
import { TableColumns } from '@amdenterpriseai/types';
import { TimeRangePeriod } from '@amdenterpriseai/types';
import { ConsumptionByProjectTableField } from '@amdenterpriseai/types';
import { UserRole } from '@amdenterpriseai/types';
import {
  TimeRange,
  TimeSeriesResponse,
  UtilizationResponse,
} from '@amdenterpriseai/types';

import { ClientSideDataTable } from '@amdenterpriseai/components';
import { AreaChart } from '@amdenterpriseai/components';
import { BarChart } from '@amdenterpriseai/components';
import { ChartTimeSelector } from '@amdenterpriseai/components';
import {
  HorizontalStatisticsCards,
  StatisticsCard,
  StatisticsCardProps,
} from '@amdenterpriseai/components';

import { isEqual } from 'lodash';
import { SortDirection } from '@amdenterpriseai/types';

interface Props {
  clusterStats: ClusterStatsResponse;
}

const columns: TableColumns<ConsumptionByProjectTableField> = [
  {
    key: ConsumptionByProjectTableField.PROJECT,
    sortable: true,
  },
  { key: ConsumptionByProjectTableField.GPU_ALLOCATION, sortable: true },
  { key: ConsumptionByProjectTableField.GPU_UTILIZATION, sortable: true },
  { key: ConsumptionByProjectTableField.RUNNING_WORKLOADS, sortable: true },
  { key: ConsumptionByProjectTableField.PENDING_WORKLOADS, sortable: true },
];

const DashboardPage = ({ clusterStats }: Props) => {
  const { t } = useTranslation('dashboard');
  const [timeRange, setTimeRange] = useState<TimeRange>(
    getCurrentTimeRange(TimeRangePeriod['1H']),
  );
  const currentTimePeriod = useRef<TimeRangePeriod>(TimeRangePeriod['1H']);

  const {
    data: gpuMemoryUsageData,
    isFetching: isGPUMemoryUsageDataFetching,
    refetch: refetchGPUMemoryUsageData,
    dataUpdatedAt: gpuMemoryUsageDataUpdatedAt,
  } = useQuery<TimeSeriesResponse>({
    queryKey: [
      'gpu-memory-utilization',
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchGPUMemoryUtilization(timeRange.start, timeRange.end);
    },
  });

  const {
    data: gpuDeviceUsageData,
    isFetching: isGPUDeviceUsageDataFetching,
    refetch: refreshGPUDeviceUsageData,
    dataUpdatedAt: gpuDeviceUsageDataUpdatedAt,
  } = useQuery<TimeSeriesResponse>({
    queryKey: [
      'gpu-device-utilization',
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchGPUDeviceUtilization(timeRange.start, timeRange.end);
    },
  });
  const latestMetricsUpdatedAt = useMemo(() => {
    const latestUpdatedAt: Date[] = [];

    if (gpuDeviceUsageDataUpdatedAt) {
      latestUpdatedAt.push(new Date(gpuDeviceUsageDataUpdatedAt));
    }

    if (gpuMemoryUsageDataUpdatedAt) {
      latestUpdatedAt.push(new Date(gpuMemoryUsageDataUpdatedAt));
    }

    return getLatestDate(latestUpdatedAt);
  }, [gpuDeviceUsageDataUpdatedAt, gpuMemoryUsageDataUpdatedAt]);

  const { data: utilizationData, isLoading: isUtilizationDataLoading } =
    useQuery<UtilizationResponse>({
      queryKey: ['project-utilization'],
      queryFn: fetchUtilization,
    });

  const handleTimeBoundChange = (
    timePeriod: TimeRangePeriod,
    timeRange: TimeRange,
  ) => {
    currentTimePeriod.current = timePeriod as TimeRangePeriod;
    setTimeRange(timeRange);
  };

  const {
    data: clusterStatisticsData,
    isLoading: isClusterStatisticsDataLoading,
  } = useQuery<ClusterStatsResponse>({
    queryKey: ['cluster-statistics'],
    queryFn: fetchClusterStatistics,
    initialData: clusterStats,
  });

  const clusterStatsCards: StatisticsCardProps[] = [
    {
      title: t('clusterAndNodes.cards.clusters.title'),
      tooltip: t('clusterAndNodes.cards.clusters.tooltip'),
      statistic: clusterStatisticsData.totalClusterCount,
    },
    {
      title: t('clusterAndNodes.cards.gpuNodes.title'),
      tooltip: t('clusterAndNodes.cards.gpuNodes.tooltip'),
      statistic: clusterStatisticsData.totalGpuNodeCount,
    },
    {
      title: t('clusterAndNodes.cards.availableGPUs.title'),
      tooltip: t('clusterAndNodes.cards.availableGPUs.tooltip'),
      statistic: clusterStatisticsData.availableGpuCount,
      upperLimit: clusterStatisticsData.totalGpuCount,
    },
    {
      title: t('clusterAndNodes.cards.allocatedGPUs.title'),
      tooltip: t('clusterAndNodes.cards.allocatedGPUs.tooltip'),
      statistic: clusterStatisticsData.allocatedGpuCount,
      upperLimit: clusterStatisticsData.availableGpuCount,
    },
  ];

  const memoryChartData = useMemo(() => {
    if (!gpuMemoryUsageData) {
      return null;
    }
    const processedData =
      gpuMemoryUsageData.data.length > 4
        ? rollupTimeSeriesData(
            gpuMemoryUsageData,
            t('common:charts.category.others'),
            'project',
          )
        : gpuMemoryUsageData.data;

    return transformTimeSeriesDataToChartData(
      processedData,
      gpuMemoryUsageData.range.timestamps,
      'project',
    );
  }, [gpuMemoryUsageData, t]);

  const deviceChartData = useMemo(() => {
    if (!gpuDeviceUsageData) {
      return null;
    }
    const processedData =
      gpuDeviceUsageData.data.length > 4
        ? rollupTimeSeriesData(
            gpuDeviceUsageData,
            t('common:charts.category.others'),
            'project',
          )
        : gpuDeviceUsageData.data;

    return transformTimeSeriesDataToChartData(
      processedData,
      gpuDeviceUsageData.range.timestamps,
      'project',
    );
  }, [gpuDeviceUsageData, t]);

  const projectsUtilization = useMemo(() => {
    return (utilizationData?.utilizationByProject || []).map((entry) => ({
      id: entry.project.id,
      name: entry.project.name,
      gpuAllocation: entry.allocatedGpusCount,
      gpuUtilization: entry.utilizedGpusCount,
      running: entry.runningWorkloadsCount,
      pending: entry.pendingWorkloadsCount,
    }));
  }, [utilizationData]);

  const memoryUtilizationChart = useMemo(
    () => (
      <AreaChart
        minValue={0}
        maxValue={100}
        type="stacked"
        className="h-64"
        tickGap={getTickGap(currentTimePeriod?.current)}
        data={memoryChartData ? memoryChartData.data : []}
        onValueChange={() => {}}
        index="date"
        categories={memoryChartData ? memoryChartData.categories : []}
        showTooltipOnNull
        valueFormatter={(number: number) => {
          return typeof number === 'number'
            ? `${displayFixedNumber(number, 2)}%`
            : t('common:charts.nodata');
        }}
        isLoading={isGPUMemoryUsageDataFetching && !memoryChartData}
        loadingText={t('common:charts.loading') || ''}
      />
    ),
    [isGPUMemoryUsageDataFetching, memoryChartData, t],
  );

  const handleChartsRefresh = useCallback(() => {
    const newRange = getCurrentTimeRange(currentTimePeriod.current);
    if (isEqual(newRange, timeRange)) {
      // Time range is the same, just refresh the data
      refetchGPUMemoryUsageData();
      refreshGPUDeviceUsageData();
    } else {
      // Time range has changed, set the new time range and react-query will auto refetch the data
      setTimeRange(newRange);
    }
  }, [refetchGPUMemoryUsageData, refreshGPUDeviceUsageData, timeRange]);

  const deviceUtilizationChart = useMemo(
    () => (
      <BarChart
        type="stacked"
        minValue={0}
        maxValue={100}
        tickGap={getTickGap(currentTimePeriod?.current)}
        className="h-64"
        data={deviceChartData ? deviceChartData.data : []}
        onValueChange={() => {}}
        index="date"
        categories={deviceChartData ? deviceChartData.categories : []}
        showTooltipOnNull
        valueFormatter={(number: number) => {
          return typeof number === 'number'
            ? `${displayFixedNumber(number, 2)}%`
            : t('common:charts.nodata');
        }}
        isLoading={isGPUDeviceUsageDataFetching && !deviceChartData}
        loadingText={t('common:charts.loading') || ''}
      />
    ),
    [deviceChartData, isGPUDeviceUsageDataFetching, t],
  );

  const chartsLoading =
    isGPUDeviceUsageDataFetching || isGPUMemoryUsageDataFetching;

  return (
    <div className="inline-flex flex-col w-full h-full max-h-full">
      <h2 className="font-semibold text-medium my-8">
        {t('clusterAndNodes.title')}
      </h2>

      <HorizontalStatisticsCards
        cards={clusterStatsCards}
        isLoading={isClusterStatisticsDataLoading}
      />
      <h2 className="font-semibold text-medium my-8">
        {t('allocationAndWorkloads.title')}
      </h2>

      <div className="flex items-start gap-4 w-full">
        <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100 grow h-full overflow-visible">
          <CardHeader className="pb-2">
            <span className="text-sm font-semibold text-foreground">
              {t('allocationAndWorkloads.consumptionByProject.title')}
            </span>
          </CardHeader>
          <CardBody className="pt-0 mt-4">
            <ClientSideDataTable
              data={projectsUtilization}
              columns={columns}
              defaultSortByField={
                ConsumptionByProjectTableField.GPU_UTILIZATION
              }
              defaultSortDirection={SortDirection.DESC}
              onRowPressed={(id: string) =>
                router.push(getProjectDashboardUrl(id))
              }
              translation={t}
              idKey={'id'}
              isLoading={isUtilizationDataLoading}
              tableVariant="transparent"
              rowActions={[
                {
                  key: 'open',
                  onPress: (item) =>
                    router.push(getProjectDashboardUrl(item.id)),
                  label: t('list.actions.open.label'),
                },
              ]}
            />
          </CardBody>
        </Card>
        <div className="flex flex-col gap-4 min-w-[300px]">
          <StatisticsCard
            title={t('allocationAndWorkloads.cards.gpuUtilization.title')}
            tooltip={t('allocationAndWorkloads.cards.gpuUtilization.tooltip')}
            statistic={utilizationData?.totalUtilizedGpusCount ?? 0}
            isLoading={isUtilizationDataLoading}
          />
          <StatisticsCard
            title={t('allocationAndWorkloads.cards.runningWorkloads.title')}
            tooltip={t('allocationAndWorkloads.cards.runningWorkloads.tooltip')}
            statistic={utilizationData?.totalRunningWorkloadsCount ?? 0}
            isLoading={isUtilizationDataLoading}
          />
          <StatisticsCard
            title={t('allocationAndWorkloads.cards.pendingWorkloads.title')}
            tooltip={t('allocationAndWorkloads.cards.pendingWorkloads.tooltip')}
            statistic={utilizationData?.totalPendingWorkloadsCount ?? 0}
            isLoading={isUtilizationDataLoading}
          />
        </div>
      </div>

      <div className="flex flex-col gap-4 py-8">
        <ChartTimeSelector
          onTimeRangeChange={handleTimeBoundChange}
          initialTimePeriod={TimeRangePeriod['1H']}
          translationPrefix="timeRange"
          onChartsRefresh={handleChartsRefresh}
          isFetching={chartsLoading}
          lastFetchedTimestamp={
            latestMetricsUpdatedAt ? latestMetricsUpdatedAt : undefined
          }
        />
        <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100">
          <CardHeader className="pb-2">
            <span className="text-sm font-semibold text-foreground">
              {t('allocationAndWorkloads.charts.gpuMemoryUtilization.title')}
            </span>
          </CardHeader>
          <CardBody className="pt-0 mt-4">{memoryUtilizationChart}</CardBody>
        </Card>
        <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100">
          <CardHeader className="pb-2">
            <span className="text-sm font-semibold text-foreground">
              {t('allocationAndWorkloads.charts.gpuDeviceUtilization.title')}
            </span>
          </CardHeader>
          <CardBody className="pt-0 mt-4">{deviceUtilizationChart}</CardBody>
        </Card>
      </div>
    </div>
  );
};

export default DashboardPage;

export async function getServerSideProps(context: any) {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

  // Redirect unauthenticated users to '/'
  const authRedirect = getAuthRedirect(session, airmMenuItems);
  if (authRedirect && !session?.user) {
    return authRedirect;
  }

  // Redirect authenticated users without access to this page to their first accessible route
  const userRoles = session?.user?.roles ?? [];
  const isAdministrator = userRoles.includes(UserRole.PLATFORM_ADMIN);

  if (!isAdministrator) {
    const destination = getFirstAccessibleRoute(airmMenuItems, userRoles);
    if (destination && destination !== '/') {
      return {
        redirect: {
          destination,
          permanent: false,
        },
      };
    }
  }

  const clusterStats = await getClusterStats(session?.accessToken as string);

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'common',
        'sharedComponents',
        'dashboard',
      ])),
      clusterStats,
    },
  };
}
