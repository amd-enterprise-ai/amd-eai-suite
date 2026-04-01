// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody, CardHeader, Skeleton } from '@heroui/react';
import { IconServer } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';

interface WorkloadClusterResourcesCardProps {
  clusterName?: string | null;
  clusterId?: string | null;
  nodesInUse?: number;
  gpuDevicesInUse?: number;
  isLoading?: boolean;
}

export const WorkloadClusterResourcesCard: React.FC<
  WorkloadClusterResourcesCardProps
> = ({ clusterName, clusterId, nodesInUse, gpuDevicesInUse, isLoading }) => {
  const { t } = useTranslation('workloads');

  return (
    <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <IconServer size={18} className="text-default-400" />
          <span className="text-sm font-medium">
            {t('details.sections.clusterAndResources')}
          </span>
        </div>
      </CardHeader>
      <CardBody className="pt-0 space-y-3 text-sm">
        {isLoading ? (
          <>
            <div className="space-y-0.5">
              <div className="text-default-500">
                {t('details.fields.cluster')}
              </div>
              <span className="text-default-400">—</span>
            </div>
            <div className="space-y-0.5">
              <div className="text-default-500">{t('details.fields.id')}</div>
              <Skeleton className="h-4 w-24 rounded" />
            </div>
            <div className="space-y-0.5">
              <div className="text-default-500">
                {t('details.fields.nodesInUse')}
              </div>
              <span className="text-default-400">—</span>
            </div>
            <div className="space-y-0.5">
              <div className="text-default-500">
                {t('details.fields.gpuDevicesInUse')}
              </div>
              <span className="text-default-400">—</span>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-0.5">
              <div className="text-default-500">
                {t('details.fields.cluster')}
              </div>
              <div>{clusterName ?? '—'}</div>
            </div>
            <div className="space-y-0.5">
              <div className="text-default-500">{t('details.fields.id')}</div>
              <div>{clusterId ?? '—'}</div>
            </div>
            <div className="space-y-0.5">
              <div className="text-default-500">
                {t('details.fields.nodesInUse')}
              </div>
              <div>{nodesInUse}</div>
            </div>
            <div className="space-y-0.5">
              <div className="text-default-500">
                {t('details.fields.gpuDevicesInUse')}
              </div>
              <div>{gpuDevicesInUse}</div>
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
};
