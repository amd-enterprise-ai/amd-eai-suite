// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tooltip } from '@heroui/react';
import { IconChevronRight } from '@tabler/icons-react';
import { useMemo } from 'react';

import { GpuDeviceInfo } from '@/types/workloads';

interface WorkloadGpuDevicesDetailProps {
  devices: GpuDeviceInfo[];
  nodeName: string;
  devicesLabel: string;
}

export const formatDeviceName = (d: GpuDeviceInfo) =>
  `gpu-${parseInt(d.gpuId, 10) + 1}`;

export const GpuDeviceEntry: React.FC<{
  device: GpuDeviceInfo;
  isOnNode: boolean;
  alwaysShowHostname?: boolean;
}> = ({ device, isOnNode, alwaysShowHostname = false }) => (
  <span
    className={`inline-flex items-center gap-0.5 ${isOnNode ? '' : 'text-default-400'}`}
  >
    {!isOnNode || alwaysShowHostname ? (
      <>
        {device.hostname} <IconChevronRight size={14} />{' '}
        {formatDeviceName(device)}
      </>
    ) : (
      formatDeviceName(device)
    )}
  </span>
);

export const GpuDevicesList: React.FC<{
  devices: GpuDeviceInfo[];
  nodeName: string;
}> = ({ devices, nodeName }) => {
  const sortedDevices = useMemo(
    () =>
      [...devices].sort(
        (a, b) =>
          a.hostname.localeCompare(b.hostname) ||
          parseInt(a.gpuId, 10) - parseInt(b.gpuId, 10),
      ),
    [devices],
  );

  return (
    <ul className="p-2 list-none space-y-1">
      {sortedDevices.map((d) => (
        <li key={`${d.hostname}-${d.gpuId}`} className="flex">
          <GpuDeviceEntry
            device={d}
            isOnNode={d.hostname === nodeName}
            alwaysShowHostname
          />
        </li>
      ))}
    </ul>
  );
};

export const WorkloadGpuDevicesDetail: React.FC<
  WorkloadGpuDevicesDetailProps
> = ({ devices, nodeName, devicesLabel }) => {
  if (devices.length === 0) return <span>-</span>;

  if (devices.length === 1) {
    return (
      <GpuDeviceEntry
        device={devices[0]}
        isOnNode={devices[0].hostname === nodeName}
      />
    );
  }

  return (
    <Tooltip
      content={<GpuDevicesList devices={devices} nodeName={nodeName} />}
      placement="top"
    >
      <span className="cursor-pointer underline">{devicesLabel}</span>
    </Tooltip>
  );
};
