// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';
import router from 'next/router';

import { displayBytesInGigabytes } from '@amdenterpriseai/utils/app';
import { displayFixedNumber } from '@amdenterpriseai/utils/app';

import { getNodeDisplayStatus } from '@/utils/node-status';

import { ClusterNode } from '@amdenterpriseai/types';
import { TableColumns } from '@amdenterpriseai/types';
import { CustomComparatorConfig } from '@amdenterpriseai/types';
import { ClusterNodesTableField } from '@amdenterpriseai/types';

import { ClientSideDataTable } from '@amdenterpriseai/components';

interface Props {
  clusterId: string;
  clusterNodes: ClusterNode[];
}

export const ClusterNodesTable = ({ clusterId, clusterNodes }: Props) => {
  const { t } = useTranslation('clusters', { keyPrefix: 'nodes' });

  const clustersData = clusterNodes;

  const columns: TableColumns<ClusterNodesTableField> = [
    { key: ClusterNodesTableField.NAME, sortable: true },
    { key: ClusterNodesTableField.STATUS, sortable: true },
    { key: ClusterNodesTableField.CPU_CORES, sortable: true },
    { key: ClusterNodesTableField.MEMORY, sortable: true },
    { key: ClusterNodesTableField.GPU_TYPE, sortable: true },
    { key: ClusterNodesTableField.GPU_COUNT, sortable: true },
    { key: ClusterNodesTableField.GPU_MEMORY, sortable: true },
  ];

  const customRenderers: Partial<
    Record<
      ClusterNodesTableField,
      (item: ClusterNode) => React.ReactNode | string
    >
  > = {
    [ClusterNodesTableField.STATUS]: (item) => {
      const displayStatus = getNodeDisplayStatus(item.status);
      return t(`detail.status.${displayStatus}`);
    },
    [ClusterNodesTableField.CPU_CORES]: (item) => {
      const cpuCores = item.cpuMilliCores / 1000;
      return `${displayFixedNumber(cpuCores)}`;
    },
    [ClusterNodesTableField.MEMORY]: (item) => {
      return `${displayBytesInGigabytes(item.memoryBytes)}`;
    },
    [ClusterNodesTableField.GPU_MEMORY]: (item) => {
      return item.gpuInfo
        ? `${displayBytesInGigabytes(item.gpuCount * item.gpuInfo.memoryBytesPerDevice)}`
        : '-';
    },
    [ClusterNodesTableField.GPU_TYPE]: (item) => {
      return item.gpuInfo ? item.gpuInfo.name : '-';
    },
  };

  const customComparator: CustomComparatorConfig<
    ClusterNode,
    ClusterNodesTableField
  > = {
    [ClusterNodesTableField.GPU_MEMORY]: (
      a: ClusterNode,
      b: ClusterNode,
    ): number =>
      a.gpuCount * (a.gpuInfo?.memoryBytesPerDevice || 0) -
      b.gpuCount * (b.gpuInfo?.memoryBytesPerDevice || 0),
  };

  return (
    <ClientSideDataTable
      data={clustersData}
      className="overflow-y-auto"
      columns={columns}
      defaultSortByField={ClusterNodesTableField.NAME}
      translation={t}
      customRenderers={customRenderers}
      customComparator={customComparator}
      idKey={'id'}
      onRowPressed={(id: string) => {
        router.push(`/clusters/${clusterId}/nodes/${id}`);
      }}
    />
  );
};
