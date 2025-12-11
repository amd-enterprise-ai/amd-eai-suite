// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { displayBytesInGigabytes } from '@/utils/app/memory';
import { displayFixedNumber } from '@/utils/app/strings';

import { ClusterNode } from '@/types/clusters';
import { TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { ClusterNodesTableField } from '@/types/enums/cluster-nodes-table-field';

import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';

interface Props {
  clusterNodes: ClusterNode[];
}

export const ClusterNodesTable = ({ clusterNodes }: Props) => {
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
      idKey={'name'}
    />
  );
};
