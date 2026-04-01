// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Accordion,
  AccordionItem,
  Card,
  CardBody,
  CardHeader,
  Tooltip,
  useDisclosure,
} from '@heroui/react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useRouter } from 'next/router';

import { useAccessControl } from '@/hooks/useAccessControl';

import {
  getCluster as fetchCluster,
  getClusterNodes as fetchClusterNodes,
  fetchSubmittableProjects,
} from '@/services/app';
import { fetchGPUDeviceUtilizationByClusterId } from '@/services/app';
import { getClusterProjects as fetchClusterProjects } from '@/services/app';
import { getClusterWorkloadsStats as fetchClusterWorkloadsStats } from '@/services/app';
import {
  getCluster,
  getClusterNodes,
  getClusterProjects,
} from '@/services/server';
import { getClusterWorkloadsStats } from '@/services/server';

import {
  doesProjectDataNeedToBeRefreshed,
  getTickGap,
  rollupTimeSeriesData,
  transformTimeSeriesDataToChartData,
} from '@amdenterpriseai/utils/app';
import { getFilteredData } from '@amdenterpriseai/utils/app';
import { displayFixedNumber } from '@amdenterpriseai/utils/app';
import { getCurrentTimeRange } from '@amdenterpriseai/utils/app';
import { authOptions } from '@amdenterpriseai/utils/server';

import {
  Cluster,
  ClusterNode,
  ClusterNodesResponse,
  ProjectsResponse,
} from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { TimeRangePeriod } from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import {
  TimeRange,
  TimeSeriesResponse,
  WorkloadStatusStatsResponse,
} from '@amdenterpriseai/types';
import { ClusterProjectsResponse, Project } from '@amdenterpriseai/types';

import { ClusterStats } from '@/components/features/clusters';
import { ClusterNodesTable } from '@/components/features/clusters/ClusterNodes';
import { ProjectTable } from '@/components/features/projects';
import { BarChart } from '@amdenterpriseai/components';
import { ChartTimeSelector } from '@amdenterpriseai/components';
import { ActionsToolbar } from '@amdenterpriseai/components';

import { isEqual } from 'lodash';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@amdenterpriseai/utils/app';
import ClusterKubeConfig from '@/components/features/clusters/ClusterKubeConfig';
import { ActionButton } from '@amdenterpriseai/components';

const translationKeySet = 'clusters';

interface Props {
  cluster: Cluster;
  clusterNodesResponse: ClusterNodesResponse;
  projectsResponse: ClusterProjectsResponse;
  workloadsStats: WorkloadStatusStatsResponse;
}

const ClusterPage: React.FC<Props> = ({
  cluster,
  clusterNodesResponse,
  projectsResponse,
  workloadsStats,
}) => {
  const router = useRouter();
  const { id } = router.query;
  const { t } = useTranslation(translationKeySet);
  const { isAdministrator } = useAccessControl();

  const [clusterNodesFilters, setClusterNodesFilters] = useState<
    ClientSideDataFilter<ClusterNode>[]
  >([]);
  const [projectFilters, setProjectFilters] = useState<
    ClientSideDataFilter<Project>[]
  >([]);
  const [timeRange, setTimeRange] = useState<TimeRange>(
    getCurrentTimeRange(TimeRangePeriod['1H']),
  );
  const currentTimePeriod = useRef<TimeRangePeriod>(TimeRangePeriod['1H']);

  const { data: clusterData } = useQuery<Cluster>({
    queryKey: ['cluster'],
    queryFn: () => fetchCluster(id as string),
    initialData: cluster,
  });

  const { data: clusterProjects } = useQuery<ClusterProjectsResponse>({
    queryKey: ['cluster', 'projects'],
    queryFn: () => fetchClusterProjects(id as string),
    initialData: projectsResponse,
    refetchInterval: (query) => {
      return !query.state.data ||
        doesProjectDataNeedToBeRefreshed(query.state.data.data)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  const { data: clusterNodesData } = useQuery<ClusterNodesResponse>({
    queryKey: ['cluster', 'nodes'],
    queryFn: () => fetchClusterNodes(id as string),
    initialData: clusterNodesResponse,
  });

  const { data: clusterWorkloadsStats } = useQuery<WorkloadStatusStatsResponse>(
    {
      queryKey: ['cluster', 'workloads', 'stats'],
      queryFn: () => fetchClusterWorkloadsStats(id as string),
      initialData: workloadsStats,
    },
  );

  const {
    data: gpuDeviceUsageData,
    isFetching: isGPUDeviceUsageDataFetching,
    refetch: refreshGPUDeviceUsageData,
    dataUpdatedAt: gpuDeviceUsageDataUpdatedAt,
  } = useQuery<TimeSeriesResponse>({
    queryKey: [
      'gpu-device-utilization',
      cluster.id,
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () => {
      return fetchGPUDeviceUtilizationByClusterId(
        id as string,
        timeRange.start,
        timeRange.end,
      );
    },
  });

  const handleTimeBoundChange = (
    timePeriod: TimeRangePeriod,
    timeRange: TimeRange,
  ) => {
    currentTimePeriod.current = timePeriod as TimeRangePeriod;
    setTimeRange(timeRange);
  };

  const filteredClusterData = useMemo(() => {
    if (!clusterNodesData?.data) {
      return [];
    }

    return getFilteredData(clusterNodesData.data, clusterNodesFilters);
  }, [clusterNodesData?.data, clusterNodesFilters]);

  const filteredProjects = useMemo(() => {
    if (!clusterProjects.data) {
      return [];
    }
    return getFilteredData(clusterProjects.data, projectFilters);
  }, [clusterProjects.data, projectFilters]);

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

  const deviceUtilizationChart = useMemo(
    () => (
      <BarChart
        type="stacked"
        minValue={0}
        maxValue={100}
        className="h-64"
        tickGap={getTickGap(currentTimePeriod?.current)}
        data={deviceChartData?.data || []}
        onValueChange={() => {}}
        index="date"
        categories={deviceChartData?.categories || []}
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

  const handleChartsRefresh = useCallback(() => {
    const newRange = getCurrentTimeRange(currentTimePeriod.current);
    if (isEqual(newRange, timeRange)) {
      // Time range is the same, just refresh the data
      refreshGPUDeviceUsageData();
    } else {
      // Time range has changed, set the new time range and react-query will auto refetch the data
      setTimeRange(newRange);
    }
  }, [refreshGPUDeviceUsageData, timeRange]);

  const handleFilterChange = useCallback(
    (filters: FilterValueMap) => {
      const newClusterNodeFilters: ClientSideDataFilter<ClusterNode>[] = [];
      const newProjectFilters: ClientSideDataFilter<Project>[] = [];

      if (filters.search) {
        newClusterNodeFilters.push({
          values: filters.search,
          compositeFields: [
            { field: 'name' },
            { field: 'gpuInfo', path: 'name' },
          ],
        });
        newProjectFilters.push({
          values: filters.search,
          field: 'name',
        });
      }

      setClusterNodesFilters(newClusterNodeFilters);
      setProjectFilters(newProjectFilters);
    },
    [setClusterNodesFilters, setProjectFilters],
  );

  const {
    isOpen: isClusterKubeConfigOpen,
    onOpen: onClusterKubeConfigOpen,
    onOpenChange: onClusterKubeConfigChange,
  } = useDisclosure();

  const filterConfig = useMemo(
    () => ({
      search: {
        name: 'search',
        className: 'min-w-72',
        label: t('list.filter.search.label'),
        placeholder: t('list.filter.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
    }),
    [t],
  );

  return (
    <div className="inline-flex flex-col w-full h-full max-h-full">
      <div className="md:py-4 lg:py-6 flex justify-between">
        <ActionsToolbar
          filterConfig={filterConfig}
          onFilterChange={handleFilterChange}
          endContent={
            <div className="flex gap-2">
              {isAdministrator && (
                <ActionButton
                  aria-label={t('workloads.actions.view') || ''}
                  onPress={() => router.push(`/clusters/${id}/workloads`)}
                >
                  {t('workloads.actions.view')}
                </ActionButton>
              )}
              <Tooltip
                content={t('config.disabled')}
                isDisabled={!!cluster.kubeApiUrl}
              >
                <span>
                  <ActionButton
                    aria-label={t('config.button') || ''}
                    onPress={onClusterKubeConfigOpen}
                    isDisabled={!cluster.kubeApiUrl}
                  >
                    {t('config.button')}
                  </ActionButton>
                </span>
              </Tooltip>
            </div>
          }
        />
      </div>
      <ClusterStats
        cluster={clusterData}
        workloadsStats={clusterWorkloadsStats}
      />
      <div className="flex flex-col gap-4 py-8">
        <ChartTimeSelector
          onTimeRangeChange={handleTimeBoundChange}
          initialTimePeriod={TimeRangePeriod['1H']}
          translationPrefix="timeRange"
          isFetching={isGPUDeviceUsageDataFetching}
          onChartsRefresh={handleChartsRefresh}
          lastFetchedTimestamp={
            gpuDeviceUsageDataUpdatedAt
              ? new Date(gpuDeviceUsageDataUpdatedAt)
              : undefined
          }
        />
        <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100">
          <CardHeader className="pb-2">
            <span className="text-sm font-semibold text-foreground">
              {t('allocationAndWorkloads.charts.gpuDeviceUtilization.title')}
            </span>
          </CardHeader>
          <CardBody className="pt-0 mt-4">{deviceUtilizationChart}</CardBody>
        </Card>
      </div>
      <Accordion
        defaultExpandedKeys={['cluster-nodes', 'cluster-quotas']}
        selectionMode="multiple"
        itemClasses={{
          title: 'uppercase',
        }}
      >
        <AccordionItem
          title={t('projects.title')}
          aria-label={t('projects.title')!}
          key="cluster-quotas"
        >
          <ProjectTable projects={filteredProjects} />
        </AccordionItem>
        <AccordionItem
          title={t('nodes.title')}
          aria-label={t('nodes.title')!}
          key="cluster-nodes"
        >
          <ClusterNodesTable
            clusterId={id as string}
            clusterNodes={filteredClusterData}
          />
        </AccordionItem>
      </Accordion>

      <ClusterKubeConfig
        isOpen={isClusterKubeConfigOpen}
        onOpenChange={onClusterKubeConfigChange}
        cluster={clusterData}
      />
    </div>
  );
};

export default ClusterPage;

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
    const [cluster, clusterNodesResponse, projectsResponse, workloadsStats] =
      await Promise.all([
        getCluster(context.params.id, session?.accessToken as string),
        getClusterNodes(context.params.id, session?.accessToken as string),
        getClusterProjects(context.params.id, session?.accessToken as string),
        getClusterWorkloadsStats(
          context.params.id,
          session?.accessToken as string,
        ),
      ]);

    const translations = await serverSideTranslations(locale, [
      'common',
      'projects',
      'sharedComponents',
      'clusters',
    ]);

    const breadcrumb = [
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.clusters?.title,
        href: '/clusters',
      },
      {
        title: `${cluster.name}`,
      },
    ];

    return {
      props: {
        ...translations,
        cluster,
        clusterNodesResponse,
        projectsResponse,
        workloadsStats,
        pageBreadcrumb: breadcrumb,
      },
    };
  } catch (error) {
    console.error('Cluster not found: ' + error);
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }
}
