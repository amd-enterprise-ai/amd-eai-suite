// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Alert } from '@heroui/react';
import { IconAlertTriangle } from '@tabler/icons-react';
import { FC, useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { ResourceType } from './constants';

import TableLine from './TableLine';

export type ResourceAllocationInformerProps = {
  isLoading: boolean;
  currentResources: {
    gpus: number;
    memoryPerGpu: number;
    cpuPerGpu: number;
  };
  quota: {
    gpus: number;
    memory: number;
    cpu: number;
  };
  requiredResources: {
    gpus: number;
    memoryPerGpu: number;
    cpuPerGpu: number;
  };
};

const ResourceAllocationInformer: FC<ResourceAllocationInformerProps> = ({
  isLoading,
  currentResources,
  quota,
  requiredResources,
}) => {
  const { t } = useTranslation('catalog', {
    keyPrefix: 'deployModal.settings.resourceAllocation',
  });

  const { gpus, memoryPerGpu, cpuPerGpu } = currentResources;

  const { totalMemory, totalCpu } = useMemo(
    () => ({
      // For 0-GPU workloads, treat as 1 GPU to avoid multiplying by 0
      totalMemory: Math.max(gpus, 1) * memoryPerGpu,
      totalCpu: Math.max(gpus, 1) * cpuPerGpu,
    }),
    [gpus, memoryPerGpu, cpuPerGpu],
  );

  const { exceedsQuota, belowRequired } = useMemo(
    () => ({
      exceedsQuota:
        gpus > quota.gpus || totalMemory > quota.memory || totalCpu > quota.cpu,
      belowRequired:
        gpus < requiredResources.gpus ||
        totalMemory <
          Math.max(requiredResources.gpus, 1) *
            requiredResources.memoryPerGpu ||
        totalCpu <
          Math.max(requiredResources.gpus, 1) * requiredResources.cpuPerGpu,
    }),
    [gpus, totalMemory, totalCpu, quota, requiredResources],
  );

  const alertContent = useMemo(() => {
    if (belowRequired && exceedsQuota) {
      return {
        color: 'text-danger',
        description: t('belowRequiredExceedsQuotaWarning'),
      };
    }
    if (belowRequired) {
      return {
        color: 'text-danger',
        description: t('belowRequiredWarning'),
      };
    }
    if (exceedsQuota) {
      return {
        color: 'text-warning',
        description: t('exceedsQuotaWarning'),
      };
    }
    return null;
  }, [belowRequired, exceedsQuota, t]);

  return (
    <div className="flex flex-col gap-4 text-small">
      <div className="text-foreground text-medium uppercase font-bold">
        {t('totalResourceAllocation')}
      </div>

      <div className="flex flex-col gap-2">
        <TableLine
          type={ResourceType.GPU}
          value={gpus}
          req={requiredResources.gpus}
          quota={quota.gpus}
          isLoading={isLoading}
        />
        <TableLine
          type={ResourceType.RAM}
          value={memoryPerGpu}
          req={
            Math.max(requiredResources.gpus, 1) * requiredResources.memoryPerGpu
          }
          multiplier={Math.max(gpus, 1)}
          quota={quota.memory}
          isLoading={isLoading}
        />
        <TableLine
          type={ResourceType.CPU}
          value={cpuPerGpu}
          req={
            Math.max(requiredResources.gpus, 1) * requiredResources.cpuPerGpu
          }
          multiplier={Math.max(gpus, 1)}
          quota={quota.cpu}
          isLoading={isLoading}
        />
      </div>

      {!isLoading && alertContent && (
        <Alert
          variant="bordered"
          color="default"
          classNames={{ base: 'pl-2' }}
          hideIconWrapper={true}
          icon={
            <>
              <IconAlertTriangle size="16" className={alertContent.color} />
            </>
          }
          description={alertContent.description}
        />
      )}
    </div>
  );
};

export default ResourceAllocationInformer;
