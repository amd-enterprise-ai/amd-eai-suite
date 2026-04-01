// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Select,
  SelectItem,
  Tab,
  Tabs,
} from '@heroui/react';
import { IconArrowLeft, IconCpu } from '@tabler/icons-react';
import { useCallback, useMemo, useRef, useState } from 'react';
import { isEqual } from 'lodash';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useRouter } from 'next/router';

import { getCluster, getClusterNode } from '@/services/server';
import {
  fetchNodeGpuClockSpeed,
  fetchNodeGpuDevices,
  fetchNodeGpuUtilization,
  fetchNodeGpuVramUtilization,
  fetchNodePowerUsage,
  fetchNodePcieBandwidth,
  fetchNodeGpuJunctionTemperature,
  fetchNodeGpuMemoryTemperature,
  fetchNodePcieEfficiency,
} from '@/services/app';

import {
  computeLinearChartMax,
  displayFixedNumber,
  displayHumanReadableBytes,
  getCurrentTimeRange,
} from '@amdenterpriseai/utils/app';
import { authOptions } from '@amdenterpriseai/utils/server';

import { useAccessControl } from '@/hooks/useAccessControl';
import { mergeGpuDeviceTimeseriesToChartData } from '@/utils/node-gpu-utilization';
import { getNodeDisplayStatus } from '@/utils/node-status';
import { getNodeStatusVariants } from '@/utils/node-status-variants';

import {
  GpuUtilizationTabId,
  PcieTrafficTabId,
  GpuTemperatureTabId,
} from '@/types/enums/clusters';
import type { NodeGpuUtilizationResponse } from '@/types/clusters';

import {
  ALL_DEVICES_KEY,
  CLOCK_SPEED_TICK_COUNT,
  GPU_LINE_CHART_COLORS,
  GPU_UTILIZATION_TAB_IDS,
  PCIE_TRAFFIC_TAB_IDS,
  GPU_TEMPERATURE_TAB_IDS,
} from '@/constants/clusters/nodeDetail';

import { AvailableChartColorsKeys, chartColors } from '@amdenterpriseai/types';
import { ClusterNode } from '@amdenterpriseai/types';
import {
  DEFAULT_CHART_TIME_PERIODS,
  TimeRangePeriod,
} from '@amdenterpriseai/types';
import { TimeRange } from '@amdenterpriseai/types';

import {
  NodeGpuDevicesTable,
  NodeGpuPowerUsageChart,
  NodeGpuTemperatureChart,
  NodeGpuUtilizationChart,
  NodeWorkloadsTable,
} from '@/components/features/clusters';

import { DataRefresher } from '@amdenterpriseai/components';
import { HorizontalStatisticsCards } from '@amdenterpriseai/components';
import { StatusDisplay } from '@amdenterpriseai/components';
import type { StatisticsCardProps } from '@amdenterpriseai/components';

interface Props {
  node: ClusterNode;
  pageBreadcrumb?: { title: string; href?: string }[];
}

function getChartColorBg(color: AvailableChartColorsKeys): string {
  return chartColors[color]?.bg ?? 'bg-gray-500';
}

function getColorForGpuUuid(
  gpuUuid: string,
  gpuColorMap: Map<string, number>,
  palette: AvailableChartColorsKeys[],
): AvailableChartColorsKeys {
  const index = gpuColorMap.get(gpuUuid) ?? 0;
  return palette[index % palette.length] ?? 'gray';
}

const translationKeySet = ['clusters', 'common', 'workloads'] as const;

const NodeDetailPage: React.FC<Props> = ({ node }) => {
  const { t } = useTranslation(translationKeySet);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAdministrator } = useAccessControl();
  const { id: clusterId, nodeId } = router.query;

  const [timeRangePeriod, setTimeRangePeriod] = useState(TimeRangePeriod['1H']);
  const currentTimePeriod = useRef<TimeRangePeriod>(TimeRangePeriod['1H']);
  const [timeRange, setTimeRange] = useState<TimeRange>(() =>
    getCurrentTimeRange(TimeRangePeriod['1H']),
  );
  const [selectedGpuDevices, setSelectedGpuDevices] = useState<Set<string>>(
    () => new Set([ALL_DEVICES_KEY]),
  );
  const [gpuUtilizationTab, setGpuUtilizationTab] =
    useState<GpuUtilizationTabId>(GpuUtilizationTabId.Memory);
  const [pcieTrafficTab, setPcieTrafficTab] = useState<PcieTrafficTabId>(
    PcieTrafficTabId.Bandwidth,
  );
  const [gpuTemperatureTab, setGpuTemperatureTab] =
    useState<GpuTemperatureTabId>(GpuTemperatureTabId.Junction);

  const nodeQueryKeyPrefix = useMemo(
    () => ['cluster', clusterId, 'node', nodeId] as const,
    [clusterId, nodeId],
  );

  const gpuUtilizationQuery = useQuery({
    queryKey: [
      ...nodeQueryKeyPrefix,
      'gpu-utilization',
      timeRange.start.toISOString(),
      timeRange.end.toISOString(),
    ],
    queryFn: () =>
      fetchNodeGpuUtilization(
        clusterId as string,
        nodeId as string,
        timeRange.start,
        timeRange.end,
      ),
    enabled: gpuUtilizationTab === GpuUtilizationTabId.GpuUsage,
  });

  const gpuVramUtilizationQuery = useQuery({
    queryKey: [
      ...nodeQueryKeyPrefix,
      'gpu-vram-utilization',
      timeRange.start.toISOString(),
      timeRange.end.toISOString(),
    ],
    queryFn: () =>
      fetchNodeGpuVramUtilization(
        clusterId as string,
        nodeId as string,
        timeRange.start,
        timeRange.end,
      ),
    enabled: gpuUtilizationTab === GpuUtilizationTabId.Memory,
  });

  const gpuClockSpeedQuery = useQuery({
    queryKey: [
      ...nodeQueryKeyPrefix,
      'gpu-clock-speed',
      timeRange.start.toISOString(),
      timeRange.end.toISOString(),
    ],
    queryFn: () =>
      fetchNodeGpuClockSpeed(
        clusterId as string,
        nodeId as string,
        timeRange.start,
        timeRange.end,
      ),
    enabled: gpuUtilizationTab === GpuUtilizationTabId.Clock,
  });

  const powerUsageQuery = useQuery({
    queryKey: [
      ...nodeQueryKeyPrefix,
      'power-usage',
      timeRange.start.toISOString(),
      timeRange.end.toISOString(),
    ],
    queryFn: () =>
      fetchNodePowerUsage(
        clusterId as string,
        nodeId as string,
        timeRange.start,
        timeRange.end,
      ),
  });

  const junctionTemperatureQuery = useQuery({
    queryKey: [
      ...nodeQueryKeyPrefix,
      'junction-temperature',
      timeRange.start.toISOString(),
      timeRange.end.toISOString(),
    ],
    queryFn: () =>
      fetchNodeGpuJunctionTemperature(
        clusterId as string,
        nodeId as string,
        timeRange.start,
        timeRange.end,
      ),
    enabled: gpuTemperatureTab === GpuTemperatureTabId.Junction,
  });

  const memoryTemperatureQuery = useQuery({
    queryKey: [
      ...nodeQueryKeyPrefix,
      'memory-temperature',
      timeRange.start.toISOString(),
      timeRange.end.toISOString(),
    ],
    queryFn: () =>
      fetchNodeGpuMemoryTemperature(
        clusterId as string,
        nodeId as string,
        timeRange.start,
        timeRange.end,
      ),
    enabled: gpuTemperatureTab === GpuTemperatureTabId.Memory,
  });

  const gpuDevicesQuery = useQuery({
    queryKey: [...nodeQueryKeyPrefix, 'gpu-devices'],
    queryFn: () => fetchNodeGpuDevices(clusterId as string, nodeId as string),
  });

  const gpuColorMap = useMemo(
    () =>
      (gpuDevicesQuery.data?.gpuDevices ?? []).reduce(
        (map, d, i) => map.set(d.gpuUuid, i),
        new Map<string, number>(),
      ),
    [gpuDevicesQuery.data?.gpuDevices],
  );

  const pcieBandwidthQuery = useQuery({
    queryKey: [
      ...nodeQueryKeyPrefix,
      'pcie-bandwidth',
      timeRange.start.toISOString(),
      timeRange.end.toISOString(),
    ],
    queryFn: () =>
      fetchNodePcieBandwidth(
        clusterId as string,
        nodeId as string,
        timeRange.start,
        timeRange.end,
      ),
    enabled: pcieTrafficTab === PcieTrafficTabId.Bandwidth,
  });

  const pcieEfficiencyQuery = useQuery({
    queryKey: [
      ...nodeQueryKeyPrefix,
      'pcie-efficiency',
      timeRange.start.toISOString(),
      timeRange.end.toISOString(),
    ],
    queryFn: () =>
      fetchNodePcieEfficiency(
        clusterId as string,
        nodeId as string,
        timeRange.start,
        timeRange.end,
      ),
    enabled: pcieTrafficTab === PcieTrafficTabId.Performance,
  });

  const nodeStatusVariants = useMemo(
    () => getNodeStatusVariants(t as (key: string) => string),
    [t],
  );

  const nodeSpecCards = useMemo((): StatisticsCardProps[] => {
    if (!node) return [];
    const tNodes = t as (key: string) => string;
    return [
      {
        title: tNodes('clusters:nodes.detail.specs.gpuType.title'),
        tooltip: tNodes('clusters:nodes.detail.specs.gpuType.tooltip'),
        statistic: 0,
        statisticFormatter: () => node.gpuInfo?.name ?? '-',
        valueClassName: 'text-lg font-extrabold truncate',
      },
      {
        title: tNodes('clusters:nodes.detail.specs.gpuMemory.title'),
        tooltip: tNodes('clusters:nodes.detail.specs.gpuMemory.tooltip'),
        statistic: node.gpuInfo
          ? node.gpuCount * node.gpuInfo.memoryBytesPerDevice
          : 0,
        statisticFormatter: (v) => (v ? displayHumanReadableBytes(v) : '-'),
      },
      {
        title: tNodes('clusters:nodes.detail.specs.cpuCores.title'),
        tooltip: tNodes('clusters:nodes.detail.specs.cpuCores.tooltip'),
        statistic: node.cpuMilliCores / 1000,
        statisticFormatter: (v) => displayFixedNumber(v),
      },
      {
        title: tNodes('clusters:nodes.detail.specs.systemMemory.title'),
        tooltip: tNodes('clusters:nodes.detail.specs.systemMemory.tooltip'),
        statistic: node.memoryBytes,
        statisticFormatter: (v) => displayHumanReadableBytes(v),
      },
    ];
  }, [node, t]);

  const gpuDeviceOptions = useMemo(() => {
    const options: { key: string; label: string; uuid?: string }[] = [
      {
        key: ALL_DEVICES_KEY,
        label: t('clusters:nodes.detail.deviceMetrics.gpuDevice.allDevices'),
      },
    ];
    const devices = gpuDevicesQuery.data?.gpuDevices ?? [];
    [...devices]
      .sort((a, b) => parseInt(a.gpuId, 10) - parseInt(b.gpuId, 10))
      .forEach((d) => {
        const label = `gpu-${parseInt(d.gpuId, 10) + 1}`;
        options.push({ key: label, label, uuid: d.gpuUuid });
      });
    return options;
  }, [gpuDevicesQuery.data?.gpuDevices, t]);

  const handleTimeRangeChange = useCallback(
    (period: TimeRangePeriod, newTimeRange: TimeRange) => {
      currentTimePeriod.current = period;
      setTimeRangePeriod(period);
      setTimeRange(newTimeRange);
    },
    [],
  );

  const handleTimeBoundChange = useCallback(
    (timePeriod: React.Key) => {
      const newTimeRange = getCurrentTimeRange(timePeriod as TimeRangePeriod);
      handleTimeRangeChange(timePeriod as TimeRangePeriod, newTimeRange);
    },
    [handleTimeRangeChange],
  );

  const activeQuery = useMemo(() => {
    if (gpuUtilizationTab === GpuUtilizationTabId.Memory)
      return gpuVramUtilizationQuery;
    if (gpuUtilizationTab === GpuUtilizationTabId.Clock)
      return gpuClockSpeedQuery;
    return gpuUtilizationQuery;
  }, [
    gpuUtilizationTab,
    gpuUtilizationQuery,
    gpuVramUtilizationQuery,
    gpuClockSpeedQuery,
  ]);

  const activeTemperatureQuery = useMemo(() => {
    if (gpuTemperatureTab === GpuTemperatureTabId.Memory)
      return memoryTemperatureQuery;
    return junctionTemperatureQuery;
  }, [gpuTemperatureTab, junctionTemperatureQuery, memoryTemperatureQuery]);

  const filterDevicesBySelection = useCallback(
    (devices: NodeGpuUtilizationResponse['gpu_devices']) => {
      const showAll =
        selectedGpuDevices.size === 0 ||
        selectedGpuDevices.has(ALL_DEVICES_KEY);
      if (showAll) return devices;
      return devices.filter((d) => {
        const key = `gpu-${parseInt(d.gpu_id, 10) + 1}`;
        return selectedGpuDevices.has(key);
      });
    },
    [selectedGpuDevices],
  );

  const gpuDevicesToShow = useMemo(
    () => filterDevicesBySelection(activeQuery.data?.gpu_devices ?? []),
    [filterDevicesBySelection, activeQuery.data?.gpu_devices],
  );

  const pcieDevicesToShow = useMemo(
    () =>
      filterDevicesBySelection(
        (pcieTrafficTab === PcieTrafficTabId.Bandwidth
          ? pcieBandwidthQuery.data?.gpu_devices
          : pcieEfficiencyQuery.data?.gpu_devices) ?? [],
      ),
    [
      filterDevicesBySelection,
      pcieTrafficTab,
      pcieBandwidthQuery.data?.gpu_devices,
      pcieEfficiencyQuery.data?.gpu_devices,
    ],
  );

  const gpuLineChartData = useMemo(
    () => mergeGpuDeviceTimeseriesToChartData(gpuDevicesToShow),
    [gpuDevicesToShow],
  );

  const gpuLineChartCategories = useMemo(
    () =>
      gpuDevicesToShow
        .slice()
        .sort((a, b) => parseInt(a.gpu_id, 10) - parseInt(b.gpu_id, 10))
        .map((d) => `gpu-${parseInt(d.gpu_id, 10) + 1}`),
    [gpuDevicesToShow],
  );

  const mappedChartColors = useMemo(
    () =>
      gpuDevicesToShow
        .slice()
        .sort((a, b) => parseInt(a.gpu_id, 10) - parseInt(b.gpu_id, 10))
        .map((d) =>
          getColorForGpuUuid(d.gpu_uuid, gpuColorMap, GPU_LINE_CHART_COLORS),
        ),
    [gpuDevicesToShow, gpuColorMap],
  );

  const chartUnit = useMemo(() => {
    if (gpuUtilizationTab === GpuUtilizationTabId.Clock) return 'MHz';
    return '%';
  }, [gpuUtilizationTab]);

  const chartValueFormatter = useMemo(() => {
    if (gpuUtilizationTab === GpuUtilizationTabId.Clock)
      return (v: number) => `${Number(v).toFixed(0)} MHz`;
    return (v: number) => `${Number(v).toFixed(0)}%`;
  }, [gpuUtilizationTab]);

  const chartMaxValue = useMemo(() => {
    if (gpuUtilizationTab === GpuUtilizationTabId.Clock) {
      const allValues = gpuDevicesToShow.flatMap(
        (d) => d.metric?.values.map((v) => v.value) ?? [],
      );
      if (allValues.length === 0) return undefined;
      return computeLinearChartMax(
        Math.max(...allValues),
        CLOCK_SPEED_TICK_COUNT,
      );
    }
    return 100;
  }, [gpuUtilizationTab, gpuDevicesToShow]);

  const chartTickCount = useMemo(() => {
    if (gpuUtilizationTab === GpuUtilizationTabId.Clock)
      return CLOCK_SPEED_TICK_COUNT;
    return undefined;
  }, [gpuUtilizationTab]);

  // Non-percentage labels (e.g. "2500 MHz") are wider and wrap to two lines at
  // the default yAxisWidth, clipping the topmost tick. Extra top margin prevents
  // that clipping.
  const chartMarginTop = useMemo(() => {
    return gpuUtilizationTab === GpuUtilizationTabId.Clock ? 20 : undefined;
  }, [gpuUtilizationTab]);

  const powerDevicesToShow = useMemo(() => {
    const devices = powerUsageQuery.data?.gpu_devices ?? [];
    const showAll =
      selectedGpuDevices.size === 0 || selectedGpuDevices.has(ALL_DEVICES_KEY);
    if (showAll) return devices;
    return devices.filter((d) => {
      const key = `gpu-${parseInt(d.gpu_id, 10) + 1}`;
      return selectedGpuDevices.has(key);
    });
  }, [powerUsageQuery.data?.gpu_devices, selectedGpuDevices]);

  const powerBarChartData = useMemo(
    () => mergeGpuDeviceTimeseriesToChartData(powerDevicesToShow),
    [powerDevicesToShow],
  );

  const powerBarChartCategories = useMemo(
    () =>
      powerDevicesToShow
        .slice()
        .sort((a, b) => parseInt(a.gpu_id, 10) - parseInt(b.gpu_id, 10))
        .map((d) => `gpu-${parseInt(d.gpu_id, 10) + 1}`),
    [powerDevicesToShow],
  );

  const pcieLineChartData = useMemo(
    () => mergeGpuDeviceTimeseriesToChartData(pcieDevicesToShow),
    [pcieDevicesToShow],
  );

  const pcieLineChartCategories = useMemo(
    () =>
      pcieDevicesToShow
        .slice()
        .sort((a, b) => parseInt(a.gpu_id, 10) - parseInt(b.gpu_id, 10))
        .map((d) => `gpu-${parseInt(d.gpu_id, 10) + 1}`),
    [pcieDevicesToShow],
  );

  const pcieLineChartColors = useMemo(
    () =>
      pcieDevicesToShow
        .slice()
        .sort((a, b) => parseInt(a.gpu_id, 10) - parseInt(b.gpu_id, 10))
        .map((d) =>
          getColorForGpuUuid(d.gpu_uuid, gpuColorMap, GPU_LINE_CHART_COLORS),
        ),
    [pcieDevicesToShow, gpuColorMap],
  );

  const tempDevicesToShow = useMemo(
    () =>
      filterDevicesBySelection(activeTemperatureQuery.data?.gpu_devices ?? []),
    [filterDevicesBySelection, activeTemperatureQuery.data?.gpu_devices],
  );

  const tempBarChartData = useMemo(
    () => mergeGpuDeviceTimeseriesToChartData(tempDevicesToShow),
    [tempDevicesToShow],
  );

  const tempBarChartCategories = useMemo(
    () =>
      tempDevicesToShow
        .slice()
        .sort((a, b) => parseInt(a.gpu_id, 10) - parseInt(b.gpu_id, 10))
        .map((d) => `gpu-${parseInt(d.gpu_id, 10) + 1}`),
    [tempDevicesToShow],
  );

  const pcieChartUnit = useMemo(
    () => (pcieTrafficTab === PcieTrafficTabId.Performance ? '%' : ''),
    [pcieTrafficTab],
  );

  const pcieChartValueFormatter = useMemo(
    () =>
      pcieTrafficTab === PcieTrafficTabId.Performance
        ? (v: number) => `${Number(v).toFixed(0)}%`
        : (v: number) => displayHumanReadableBytes(v) + '/s',
    [pcieTrafficTab],
  );

  const pcieChartMaxValue = useMemo(
    () => (pcieTrafficTab === PcieTrafficTabId.Performance ? 100 : undefined),
    [pcieTrafficTab],
  );

  const pcieChartMarginTop = useMemo(
    () => (pcieTrafficTab === PcieTrafficTabId.Bandwidth ? 20 : undefined),
    [pcieTrafficTab],
  );

  const handleChartsRefresh = useCallback(() => {
    const newRange = getCurrentTimeRange(currentTimePeriod.current);
    if (isEqual(newRange, timeRange)) {
      queryClient.invalidateQueries({
        queryKey: nodeQueryKeyPrefix,
      });
    } else {
      setTimeRange(newRange);
    }
  }, [timeRange, queryClient, nodeQueryKeyPrefix]);

  const handleBack = useCallback(() => {
    router.push(`/clusters/${clusterId}`);
  }, [router, clusterId]);

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 min-w-0">
          <Button
            size="sm"
            isIconOnly
            variant="light"
            onPress={handleBack}
            aria-label={t('common:actions.back.title')}
          >
            <IconArrowLeft size={16} />
          </Button>
          <span className="text-base font-medium truncate">
            {node?.name} node
          </span>
          {node ? (
            <span
              aria-label={t(
                `clusters:nodes.detail.status.${getNodeDisplayStatus(node.status)}`,
              )}
            >
              <StatusDisplay
                type={getNodeDisplayStatus(node.status)}
                variants={nodeStatusVariants}
              />
            </span>
          ) : null}
        </div>
      </div>

      {nodeSpecCards.length > 0 && (
        <section className="flex flex-col gap-4">
          <HorizontalStatisticsCards cards={nodeSpecCards} />
        </section>
      )}

      <section className="flex flex-col gap-4">
        <div className="flex flex-row items-center justify-between gap-4 flex-wrap">
          <h3 className="text-base font-medium">
            {t('clusters:nodes.detail.deviceMetrics.title')}
          </h3>
          <div className="flex items-center gap-3 flex-nowrap">
            <span className="whitespace-nowrap">
              <DataRefresher
                onRefresh={handleChartsRefresh}
                lastFetchedTimestamp={(() => {
                  const ts = Math.max(
                    activeQuery.dataUpdatedAt,
                    powerUsageQuery.dataUpdatedAt,
                    activeTemperatureQuery.dataUpdatedAt,
                    pcieBandwidthQuery.dataUpdatedAt,
                    pcieEfficiencyQuery.dataUpdatedAt,
                  );
                  return ts > 0 ? new Date(ts) : undefined;
                })()}
                isRefreshing={
                  activeQuery.isFetching ||
                  powerUsageQuery.isFetching ||
                  activeTemperatureQuery.isFetching ||
                  pcieBandwidthQuery.isFetching ||
                  pcieEfficiencyQuery.isFetching
                }
                compact
              />
            </span>
            <Select
              aria-label={t(
                'clusters:nodes.detail.deviceMetrics.gpuDevice.label',
              )}
              className="min-w-64"
              selectionMode="multiple"
              selectedKeys={selectedGpuDevices}
              onSelectionChange={(keys) => {
                const newSet = new Set(keys as Iterable<string>);
                const hadAllDevices = selectedGpuDevices.has(ALL_DEVICES_KEY);
                if (newSet.size === 0) {
                  setSelectedGpuDevices(new Set([ALL_DEVICES_KEY]));
                  return;
                }
                if (newSet.has(ALL_DEVICES_KEY) && !hadAllDevices) {
                  setSelectedGpuDevices(new Set([ALL_DEVICES_KEY]));
                  return;
                }
                if (
                  newSet.has(ALL_DEVICES_KEY) &&
                  hadAllDevices &&
                  newSet.size > 1
                ) {
                  const onlyGpus = new Set(
                    Array.from(newSet).filter((k) => k !== ALL_DEVICES_KEY),
                  );
                  setSelectedGpuDevices(onlyGpus);
                  return;
                }
                if (newSet.has(ALL_DEVICES_KEY) && newSet.size === 1) {
                  setSelectedGpuDevices(new Set([ALL_DEVICES_KEY]));
                  return;
                }
                setSelectedGpuDevices(newSet);
              }}
              disallowEmptySelection
              startContent={
                <IconCpu size={16} className="text-default-400 shrink-0" />
              }
              renderValue={() => {
                const sel = selectedGpuDevices;
                if (sel.size === 0 || sel.has(ALL_DEVICES_KEY)) {
                  return t(
                    'clusters:nodes.detail.deviceMetrics.gpuDevice.allDevices',
                  );
                }
                if (sel.size === 1) return Array.from(sel)[0];
                return t(
                  'clusters:nodes.detail.deviceMetrics.gpuDevice.selectedCount',
                  { count: sel.size },
                );
              }}
            >
              {gpuDeviceOptions.map((opt, idx) => (
                <SelectItem
                  key={opt.key}
                  textValue={opt.label}
                  startContent={
                    opt.key === ALL_DEVICES_KEY ? (
                      <IconCpu
                        size={16}
                        className="text-default-400 shrink-0"
                      />
                    ) : (
                      <span
                        className={`size-2 rounded-sm shrink-0 ${getChartColorBg(opt.uuid ? getColorForGpuUuid(opt.uuid, gpuColorMap, GPU_LINE_CHART_COLORS) : 'gray')}`}
                      />
                    )
                  }
                >
                  {opt.label}
                </SelectItem>
              ))}
            </Select>
            <Tabs
              aria-label={t('common:timeRange.description') || ''}
              classNames={{ base: 'justify-end w-full' }}
              selectedKey={timeRangePeriod}
              items={DEFAULT_CHART_TIME_PERIODS.map((id) => ({ id }))}
              placement="top"
              onSelectionChange={handleTimeBoundChange}
            >
              {(item) => (
                <Tab
                  key={item.id}
                  title={t(`common:timeRange.range.${item.id}`)}
                />
              )}
            </Tabs>
          </div>
        </div>
        <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100 min-h-[120px]">
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-center justify-between gap-2 w-full">
              <span className="text-sm font-semibold text-foreground">
                {t('clusters:nodes.detail.deviceMetrics.gpuUtilization.title')}
              </span>
              <Tabs
                size="sm"
                variant="solid"
                aria-label={t(
                  'clusters:nodes.detail.deviceMetrics.gpuUtilization.title',
                )}
                selectedKey={gpuUtilizationTab}
                onSelectionChange={(key) =>
                  setGpuUtilizationTab(key as GpuUtilizationTabId)
                }
                classNames={{
                  base: 'w-fit',
                  panel: 'hidden',
                  tabList: 'dark:bg-default-200',
                  cursor: 'dark:bg-default-100',
                }}
                items={GPU_UTILIZATION_TAB_IDS.map((tabId) => ({
                  id: tabId,
                  title:
                    tabId === GpuUtilizationTabId.Memory
                      ? t(
                          'clusters:nodes.detail.deviceMetrics.gpuUtilization.tabMemoryUtilization',
                        )
                      : tabId === GpuUtilizationTabId.Clock
                        ? t(
                            'clusters:nodes.detail.deviceMetrics.gpuUtilization.tabClockSpeed',
                          )
                        : t(
                            'clusters:nodes.detail.deviceMetrics.gpuUtilization.tabGpuUsage',
                          ),
                }))}
              >
                {(item) => <Tab key={item.id} title={item.title} />}
              </Tabs>
            </div>
          </CardHeader>
          <CardBody className="pt-0 mt-4">
            <NodeGpuUtilizationChart
              data={gpuLineChartData}
              categories={gpuLineChartCategories}
              colors={mappedChartColors}
              isLoading={activeQuery.isLoading || gpuDevicesQuery.isLoading}
              showNoData={
                !activeQuery.isLoading && gpuDevicesToShow.length === 0
              }
              noDataMessage={t('clusters:nodes.detail.deviceMetrics.noData')}
              loadingText={t('common:loading', 'Loading...')}
              unit={chartUnit}
              valueFormatter={chartValueFormatter}
              maxValue={chartMaxValue}
              yAxisTickCount={chartTickCount}
              marginTop={chartMarginTop}
            />
          </CardBody>
        </Card>
        <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100 min-h-[120px]">
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-center justify-between gap-2 w-full">
              <span className="text-sm font-semibold text-foreground">
                {t('clusters:nodes.detail.deviceMetrics.gpuTemperature.title')}
              </span>
              <Tabs
                size="sm"
                variant="solid"
                aria-label={t(
                  'clusters:nodes.detail.deviceMetrics.gpuTemperature.title',
                )}
                selectedKey={gpuTemperatureTab}
                onSelectionChange={(key) =>
                  setGpuTemperatureTab(key as GpuTemperatureTabId)
                }
                classNames={{
                  base: 'w-fit',
                  panel: 'hidden',
                  tabList: 'dark:bg-default-200',
                  cursor: 'dark:bg-default-100',
                }}
                items={GPU_TEMPERATURE_TAB_IDS.map((tabId) => ({
                  id: tabId,
                  title:
                    tabId === GpuTemperatureTabId.Memory
                      ? t(
                          'clusters:nodes.detail.deviceMetrics.gpuTemperature.tabMemoryTemperature',
                        )
                      : t(
                          'clusters:nodes.detail.deviceMetrics.gpuTemperature.tabJunctionTemperature',
                        ),
                }))}
              >
                {(item) => <Tab key={item.id} title={item.title} />}
              </Tabs>
            </div>
          </CardHeader>
          <CardBody className="pt-0 mt-4">
            <NodeGpuTemperatureChart
              data={tempBarChartData}
              categories={tempBarChartCategories}
              colors={mappedChartColors}
              isLoading={
                activeTemperatureQuery.isLoading || gpuDevicesQuery.isLoading
              }
              showNoData={
                !activeTemperatureQuery.isLoading &&
                tempDevicesToShow.length === 0
              }
              noDataMessage={t(
                'clusters:nodes.detail.deviceMetrics.noTemperatureData',
              )}
              loadingText={t('common:loading', 'Loading...')}
            />
          </CardBody>
        </Card>
        <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100 min-h-[120px]">
          <CardHeader className="pb-2">
            <span className="text-sm font-semibold text-foreground">
              {t(
                'clusters:nodes.detail.deviceMetrics.gpuPowerConsumption.title',
              )}
            </span>
          </CardHeader>
          <CardBody className="pt-0 mt-4">
            <NodeGpuPowerUsageChart
              data={powerBarChartData}
              categories={powerBarChartCategories}
              colors={mappedChartColors}
              isLoading={powerUsageQuery.isLoading || gpuDevicesQuery.isLoading}
              showNoData={
                !powerUsageQuery.isLoading && powerDevicesToShow.length === 0
              }
              noDataMessage={t(
                'clusters:nodes.detail.deviceMetrics.noPowerData',
              )}
              loadingText={t('common:loading', 'Loading...')}
            />
          </CardBody>
        </Card>

        <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100 min-h-[120px]">
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-center justify-between gap-2 w-full">
              <span className="text-sm font-semibold text-foreground">
                {t('clusters:nodes.detail.deviceMetrics.pcieTraffic.title')}
              </span>
              <Tabs
                size="sm"
                variant="solid"
                aria-label={t(
                  'clusters:nodes.detail.deviceMetrics.pcieTraffic.title',
                )}
                selectedKey={pcieTrafficTab}
                onSelectionChange={(key) =>
                  setPcieTrafficTab(key as PcieTrafficTabId)
                }
                classNames={{
                  base: 'w-fit',
                  panel: 'hidden',
                  tabList: 'dark:bg-default-200',
                  cursor: 'dark:bg-default-100',
                }}
                items={PCIE_TRAFFIC_TAB_IDS.map((tabId) => ({
                  id: tabId,
                  title:
                    tabId === PcieTrafficTabId.Bandwidth
                      ? t(
                          'clusters:nodes.detail.deviceMetrics.pcieTraffic.tabBandwidth',
                        )
                      : t(
                          'clusters:nodes.detail.deviceMetrics.pcieTraffic.tabPerformance',
                        ),
                }))}
              >
                {(item) => <Tab key={item.id} title={item.title} />}
              </Tabs>
            </div>
          </CardHeader>
          <CardBody className="pt-0 mt-4">
            <NodeGpuUtilizationChart
              data={pcieLineChartData}
              categories={pcieLineChartCategories}
              colors={pcieLineChartColors}
              isLoading={
                gpuDevicesQuery.isLoading ||
                (pcieTrafficTab === PcieTrafficTabId.Bandwidth
                  ? pcieBandwidthQuery.isLoading
                  : pcieEfficiencyQuery.isLoading)
              }
              showNoData={
                pcieTrafficTab === PcieTrafficTabId.Bandwidth
                  ? !pcieBandwidthQuery.isLoading &&
                    pcieDevicesToShow.length === 0
                  : !pcieEfficiencyQuery.isLoading &&
                    pcieDevicesToShow.length === 0
              }
              noDataMessage={t('clusters:nodes.detail.deviceMetrics.noData')}
              loadingText={t('common:loading', 'Loading...')}
              unit={pcieChartUnit}
              valueFormatter={pcieChartValueFormatter}
              maxValue={pcieChartMaxValue}
              marginTop={pcieChartMarginTop}
              minValue={0}
            />
          </CardBody>
        </Card>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-base font-medium">
          {t('clusters:nodes.detail.gpuDevices.title')}
        </h3>
        <NodeGpuDevicesTable
          gpuDevices={gpuDevicesQuery.data?.gpuDevices ?? []}
          isLoading={gpuDevicesQuery.isLoading}
        />
      </section>

      {isAdministrator && (
        <section className="flex flex-col gap-4">
          <h3 className="text-base font-medium">
            {t('clusters:nodes.detail.workloads.title')}
          </h3>
          <NodeWorkloadsTable
            clusterId={clusterId as string}
            nodeId={nodeId as string}
            nodeName={node?.name ?? ''}
          />
        </section>
      )}
    </div>
  );
};

export default NodeDetailPage;

export async function getServerSideProps(context: any) {
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

  try {
    const clusterId = context.params.id;
    const nodeId = context.params.nodeId;
    const accessToken = session.accessToken as string;

    const [node, cluster] = await Promise.all([
      getClusterNode(clusterId, nodeId, accessToken),
      getCluster(clusterId, accessToken),
    ]);

    const translations = await serverSideTranslations(locale, [
      'common',
      'clusters',
      'workloads',
    ]);

    const clustersTitle =
      (
        translations._nextI18Next?.initialI18nStore?.[locale]?.clusters as {
          title?: string;
        }
      )?.title ?? 'Clusters';

    const breadcrumb = [
      { title: clustersTitle, href: '/clusters' },
      { title: cluster.name, href: `/clusters/${clusterId}` },
      { title: node.name },
    ];

    return {
      props: {
        ...translations,
        node,
        pageBreadcrumb: breadcrumb,
      },
    };
  } catch (error) {
    console.error('Node not found:', error);
    const clusterId = context.params?.id;
    return {
      redirect: {
        destination: clusterId ? `/clusters/${clusterId}` : '/',
        permanent: false,
      },
    };
  }
}
