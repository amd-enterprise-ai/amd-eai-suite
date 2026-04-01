// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody, Button } from '@heroui/react';
import { IconArrowLeft, IconTrash } from '@tabler/icons-react';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { GetServerSidePropsContext } from 'next';
import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useRouter } from 'next/router';

import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  getWorkloadMetrics,
  getWorkloadVramUtilization,
  getWorkloadJunctionTemperature,
  getWorkloadPowerUsage,
  deleteWorkload,
} from '@/services/app';

import { getWorkload } from '@/services/server/workloads';
import { formatDeviceName } from '@/components/features/clusters/NodeWorkloadsTable/WorkloadGpuDevicesDetail';
import { getClusterNodes } from '@/services/server/clusters';

import { getWorkloadStatusVariants } from '@amdenterpriseai/utils/app';
import { getCurrentTimeRange } from '@amdenterpriseai/utils/app';
import { authOptions } from '@amdenterpriseai/utils/server';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import { TimeRangePeriod, ClusterNode } from '@amdenterpriseai/types';

import { WorkloadResponse, WorkloadMetricsDetails } from '@/types/workloads';

import { ChartTimeSelector } from '@amdenterpriseai/components';
import { StatusDisplay } from '@amdenterpriseai/components';

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import { GpuDeviceMetricsGrid } from '@/components/features/workloads/GpuDeviceMetricsGrid';
import { GpuMetricsLoadingSkeleton } from '@/components/features/workloads/GpuMetricsLoadingSkeleton';
import { WorkloadBasicInfoCard } from '@/components/features/workloads/WorkloadBasicInfoCard';
import { WorkloadClusterResourcesCard } from '@/components/features/workloads/WorkloadClusterResourcesCard';
import { WorkloadTimelineCard } from '@/components/features/workloads/WorkloadTimelineCard';

interface Props {
  pageBreadcrumb?: { title: string; href?: string }[];
  workload: WorkloadResponse;
  clusterNodes: ClusterNode[];
}

const WorkloadDetailPage: React.FC<Props> = ({ workload, clusterNodes }) => {
  const { t } = useTranslation(['workloads', 'common']);
  const { t: workloadsT } = useTranslation('workloads');
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();
  const { id } = router.query;

  const [timeRange, setTimeRange] = useState(() =>
    getCurrentTimeRange(TimeRangePeriod['1H']),
  );
  const currentTimePeriod = useRef<TimeRangePeriod>(TimeRangePeriod['1H']);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const { data: workloadMetrics, refetch: refetchWorkloadMetrics } =
    useQuery<WorkloadMetricsDetails>({
      queryKey: ['workload', id, 'metrics'],
      queryFn: async () => {
        const data = await getWorkloadMetrics(id as string);
        if (data == null) throw new Error('Workload metrics not found');
        return data;
      },
      enabled: !!id,
    });

  const gpuMetricsParams = {
    start: timeRange.start.toISOString(),
    end: timeRange.end.toISOString(),
  };

  const vramQuery = useQuery({
    queryKey: [
      'workload',
      id,
      'vram-utilization',
      gpuMetricsParams.start,
      gpuMetricsParams.end,
    ],
    queryFn: () => getWorkloadVramUtilization(id as string, gpuMetricsParams),
    enabled: !!id,
  });

  const temperatureQuery = useQuery({
    queryKey: [
      'workload',
      id,
      'junction-temperature',
      gpuMetricsParams.start,
      gpuMetricsParams.end,
    ],
    queryFn: () =>
      getWorkloadJunctionTemperature(id as string, gpuMetricsParams),
    enabled: !!id,
  });

  const powerQuery = useQuery({
    queryKey: [
      'workload',
      id,
      'power-usage',
      gpuMetricsParams.start,
      gpuMetricsParams.end,
    ],
    queryFn: () => getWorkloadPowerUsage(id as string, gpuMetricsParams),
    enabled: !!id,
  });

  const isGpuMetricsLoading =
    vramQuery.isLoading || temperatureQuery.isLoading || powerQuery.isLoading;
  const isGpuMetricsFetching =
    vramQuery.isFetching ||
    temperatureQuery.isFetching ||
    powerQuery.isFetching;
  const gpuMetricsUpdatedAt =
    Math.max(
      vramQuery.dataUpdatedAt ?? 0,
      temperatureQuery.dataUpdatedAt ?? 0,
      powerQuery.dataUpdatedAt ?? 0,
    ) || undefined;

  const gpuDevices = useMemo(() => {
    const toSeries = (values: { value: number; timestamp: string }[]) =>
      values.map((v) => ({ time: v.timestamp, value: v.value }));
    const latestValue = (values: { value: number }[]) =>
      values.length > 0 ? values[values.length - 1].value : null;

    const vramDevices = vramQuery.data?.gpuDevices ?? [];
    const tempDevices = temperatureQuery.data?.gpuDevices ?? [];
    const powerDevices = powerQuery.data?.gpuDevices ?? [];

    const vramByUuid = new Map(vramDevices.map((d) => [d.gpuUuid, d]));
    const tempByUuid = new Map(tempDevices.map((d) => [d.gpuUuid, d]));
    const powerByUuid = new Map(powerDevices.map((d) => [d.gpuUuid, d]));

    const uniqueDevices = new Map(
      [...vramDevices, ...tempDevices, ...powerDevices].map((d) => [
        d.gpuUuid,
        { gpuUuid: d.gpuUuid, gpuId: d.gpuId, hostname: d.hostname },
      ]),
    );

    return Array.from(uniqueDevices.values())
      .map((base) => {
        const vram = vramByUuid.get(base.gpuUuid)?.metric?.values ?? [];
        const temp = tempByUuid.get(base.gpuUuid)?.metric?.values ?? [];
        const power = powerByUuid.get(base.gpuUuid)?.metric?.values ?? [];
        return {
          ...base,
          displayLabel: formatDeviceName(base),
          vramUtilizationPct: latestValue(vram),
          junctionTemperatureC: latestValue(temp),
          powerUsageW: latestValue(power),
          vramUtilizationSeries: toSeries(vram),
          junctionTemperatureSeries: toSeries(temp),
          powerUsageSeries: toSeries(power),
        };
      })
      .sort(
        (a, b) =>
          a.hostname.localeCompare(b.hostname) ||
          parseInt(a.gpuId, 10) - parseInt(b.gpuId, 10),
      );
  }, [vramQuery.data, temperatureQuery.data, powerQuery.data]);

  const nodesByHostname = useMemo(
    () =>
      clusterNodes.reduce(
        (map, node) => map.set(node.name, node),
        new Map<string, ClusterNode>(),
      ),
    [clusterNodes],
  );

  const { mutate: deleteWorkloadMutation } = useMutation({
    mutationFn: deleteWorkload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workload', id] });
      queryClient.invalidateQueries({ queryKey: ['cluster', 'workloads'] });
      toast.success(t('workloads:list.actions.delete.notification.success'));
      router.back();
    },
    onError: (error) => {
      toast.error(
        t('workloads:list.actions.delete.notification.error'),
        error as APIRequestError,
      );
    },
  });

  const handleTimeRangeChange = useCallback(
    (period: TimeRangePeriod, newTimeRange: { start: Date; end: Date }) => {
      currentTimePeriod.current = period;
      setTimeRange(newTimeRange);
    },
    [],
  );

  const handleChartsRefresh = useCallback(() => {
    const newRange = getCurrentTimeRange(currentTimePeriod.current);
    setTimeRange(newRange);
    refetchWorkloadMetrics();
  }, [refetchWorkloadMetrics]);

  const hasGpuMetrics = gpuDevices.length > 0;
  const showGpuLoadingPlaceholder =
    isGpuMetricsLoading && gpuDevices.length === 0;

  const moduleName = workload.displayName || workload.name;

  return (
    <div className="inline-flex flex-col w-full max-w-6xl mx-auto p-4 md:p-6 gap-6">
      {/* Header: breadcrumb (back + module name + status) and actions on one row */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 min-w-0">
          <Button
            size="sm"
            isIconOnly
            variant="light"
            onPress={() => router.back()}
            aria-label={t('workloads:details.actions.back')}
          >
            <IconArrowLeft size={16} />
          </Button>
          <span className="text-base font-medium truncate">{moduleName}</span>
          <StatusDisplay
            type={workload.status}
            variants={getWorkloadStatusVariants(workloadsT)}
          />
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            color="danger"
            variant="flat"
            size="sm"
            startContent={<IconTrash size={16} />}
            onPress={() => setIsDeleteModalOpen(true)}
          >
            {t('workloads:details.actions.delete')}
          </Button>
        </div>
      </div>

      {/* Resource utilization */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-row items-center justify-between gap-4 flex-wrap">
          <h3 className="text-base font-medium">
            {t('workloads:details.sections.resourceUtilization')}
          </h3>
          <div className="flex items-center gap-3">
            <ChartTimeSelector
              onTimeRangeChange={handleTimeRangeChange}
              onChartsRefresh={handleChartsRefresh}
              isFetching={isGpuMetricsFetching}
              lastFetchedTimestamp={
                gpuMetricsUpdatedAt ? new Date(gpuMetricsUpdatedAt) : undefined
              }
              initialTimePeriod={TimeRangePeriod['1H']}
            />
          </div>
        </div>
        {showGpuLoadingPlaceholder ? (
          <GpuMetricsLoadingSkeleton />
        ) : !hasGpuMetrics ? (
          <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100">
            <CardBody>
              <p className="text-default-500 text-sm">
                {t('workloads:details.fields.noGpuMetrics')}
              </p>
            </CardBody>
          </Card>
        ) : (
          <GpuDeviceMetricsGrid
            devices={gpuDevices}
            nodesByHostname={nodesByHostname}
            clusterId={workload?.clusterId}
            isFetching={isGpuMetricsFetching}
          />
        )}
      </section>

      {/* Information */}
      <section>
        <h3 className="text-base font-medium mb-4">
          {t('workloads:details.sections.workloadInformation')}
        </h3>
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex flex-col gap-4 md:w-1/2">
            <WorkloadBasicInfoCard
              name={workload.displayName || workload.name}
              workloadId={workload.id}
              createdBy={workload.createdBy}
            />
            <WorkloadTimelineCard
              createdAt={workload.createdAt}
              updatedAt={workload.updatedAt}
              queueTime={workloadMetrics?.queueTime}
              runningTime={workloadMetrics?.runningTime}
            />
          </div>
          <div className="md:w-1/2">
            <WorkloadClusterResourcesCard
              clusterName={workloadMetrics?.clusterName}
              clusterId={workloadMetrics?.clusterId}
              nodesInUse={workloadMetrics?.nodesInUse}
              gpuDevicesInUse={workloadMetrics?.gpuDevicesInUse}
              isLoading={!workloadMetrics}
            />
          </div>
        </div>
      </section>

      <DeleteWorkloadModal
        isOpen={isDeleteModalOpen}
        onOpenChange={setIsDeleteModalOpen}
        workload={workload}
        onConfirmAction={(workloadId) => deleteWorkloadMutation(workloadId)}
      />
    </div>
  );
};

export default WorkloadDetailPage;

export async function getServerSideProps(context: GetServerSidePropsContext) {
  const locale = context.locale ?? 'en';
  const session = await getServerSession(context.req, context.res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: { destination: '/', permanent: false },
    };
  }

  const workloadId = context.params?.id as string;

  try {
    const workload = (await getWorkload({
      accessToken: session.accessToken as string,
      workloadId,
    })) as WorkloadResponse;

    const clusterId = workload?.clusterId;

    const clusterNodesResponse = clusterId
      ? await getClusterNodes(clusterId, session.accessToken as string).catch(
          () => ({ data: [] }),
        )
      : { data: [] };

    const translations = await serverSideTranslations(locale, [
      'common',
      'workloads',
    ]);

    const breadcrumb = [{ title: 'Workload details' }];
    return {
      props: {
        ...translations,
        pageBreadcrumb: breadcrumb,
        workload,
        clusterNodes: clusterNodesResponse.data,
      },
    };
  } catch (error) {
    console.error('Workload retrieval failure: ' + error);
    return {
      redirect: { destination: '/', permanent: false },
    };
  }
}
