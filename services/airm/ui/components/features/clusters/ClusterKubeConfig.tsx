// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useQuery } from '@tanstack/react-query';

import { Trans, useTranslation } from 'next-i18next';

import { fetchClusterKubeConfig } from '@/services/app/clusters';

import {
  Cluster,
  ClusterKubeConfig as ClusterKubeConfigType,
} from '@/types/clusters';

import { DrawerDisplay } from '@/components/shared/Drawer';

import { Snippet, Spinner } from '@heroui/react';

interface Props {
  isOpen: boolean;
  onOpenChange: () => void;
  cluster: Cluster;
}

export const ClusterKubeConfig: React.FC<Props> = ({
  isOpen,
  onOpenChange,
  cluster,
}) => {
  const { t } = useTranslation('clusters');

  const { data } = useQuery<ClusterKubeConfigType>({
    queryKey: ['cluster', cluster.id, 'kube-config'],
    queryFn: () => fetchClusterKubeConfig(cluster.id),
    enabled: isOpen,
  });

  return (
    <DrawerDisplay
      isOpen={isOpen}
      title={t('config.title')}
      onOpenChange={onOpenChange}
    >
      <div>
        <Trans parent="p">
          {t('config.description', { name: cluster.name })}
        </Trans>

        {!data && (
          <div className="w-full mt-10 flex justify-center h-full">
            <Spinner />
          </div>
        )}
        {!!data && (
          <Snippet
            symbol=""
            classNames={{
              base: 'mt-8 w-full',
              pre: 'whitespace-pre-wrap overflow-x-auto',
            }}
          >
            <span>{data?.kubeConfig}</span>
          </Snippet>
        )}
      </div>
    </DrawerDisplay>
  );
};

export default ClusterKubeConfig;
