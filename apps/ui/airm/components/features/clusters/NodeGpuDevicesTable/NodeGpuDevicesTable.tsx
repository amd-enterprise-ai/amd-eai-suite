// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import {
  displayFixedNumber,
  displayTimestamp,
} from '@amdenterpriseai/utils/app';

import { TableColumns } from '@amdenterpriseai/types';

import { NodeGpuDevicesTableField } from '@/types/enums/clusters';

import { ClientSideDataTable } from '@amdenterpriseai/components';

import type { NodeGpuDevice } from '@/types/clusters';

interface Props {
  gpuDevices: NodeGpuDevice[];
  isLoading: boolean;
}

const T_PREFIX = 'nodes.detail.gpuDevices';

function formatGpuId(gpuId: string): string {
  const index = parseInt(gpuId, 10);
  return `gpu-${isNaN(index) ? gpuId : index + 1}`;
}

const columns: TableColumns<NodeGpuDevicesTableField> = [
  { key: NodeGpuDevicesTableField.GPU_ID, sortable: true },
  { key: NodeGpuDevicesTableField.PRODUCT_NAME, sortable: true },
  { key: NodeGpuDevicesTableField.TEMPERATURE, sortable: true },
  { key: NodeGpuDevicesTableField.POWER_CONSUMPTION, sortable: true },
  { key: NodeGpuDevicesTableField.VRAM_UTILIZATION, sortable: true },
  { key: NodeGpuDevicesTableField.LAST_UPDATED, sortable: true },
];

export const NodeGpuDevicesTable: React.FC<Props> = ({
  gpuDevices,
  isLoading,
}) => {
  const { t } = useTranslation('clusters', { keyPrefix: T_PREFIX });

  const customRenderers: Partial<
    Record<
      NodeGpuDevicesTableField,
      (item: NodeGpuDevice) => React.ReactNode | string
    >
  > = {
    [NodeGpuDevicesTableField.GPU_ID]: (item) => formatGpuId(item.gpuId),
    [NodeGpuDevicesTableField.PRODUCT_NAME]: (item) => item.productName ?? '-',
    [NodeGpuDevicesTableField.TEMPERATURE]: (item) =>
      item.temperature != null
        ? t('units.celsius', { value: displayFixedNumber(item.temperature, 1) })
        : '-',
    [NodeGpuDevicesTableField.POWER_CONSUMPTION]: (item) =>
      item.powerConsumption != null
        ? t('units.watts', {
            value: displayFixedNumber(item.powerConsumption, 1),
          })
        : '-',
    [NodeGpuDevicesTableField.VRAM_UTILIZATION]: (item) =>
      item.vramUtilization != null
        ? t('units.percent', {
            value: displayFixedNumber(item.vramUtilization, 1),
          })
        : '-',
    [NodeGpuDevicesTableField.LAST_UPDATED]: (item) =>
      item.lastUpdated ? displayTimestamp(new Date(item.lastUpdated)) : '-',
  };

  return (
    <ClientSideDataTable
      data={gpuDevices}
      columns={columns}
      defaultSortByField={NodeGpuDevicesTableField.GPU_ID}
      translation={t}
      customRenderers={customRenderers}
      idKey="gpuId"
      isLoading={isLoading}
    />
  );
};
