// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Spinner, useDisclosure } from '@heroui/react';
import { IconRocket, IconTag } from '@tabler/icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { getFilteredData } from '@amdenterpriseai/utils/app';

import { FilterComponentType } from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';

import { ActionsToolbar } from '@amdenterpriseai/components';

import { AIMCard } from './AIMCard';
import { DeployAIMDrawer } from './DeployAIMDrawer';
import UndeployAIMModal from './UndeployAIMModal';
import AIMConnectModal from './AIMConnectModal';

import { useProject } from '@/contexts/ProjectContext';
import {
  getAimClusterModels,
  transformToAggregatedAIMs,
  undeployAim,
} from '@/lib/app/aims';
import { AIMWorkloadStatus, ParsedAIM, AggregatedAIM } from '@/types/aims';
import { useRouter } from 'next/router';
import { APIRequestError } from '@amdenterpriseai/utils/app';

const AIMS_REFETCH_INTERVAL = 30000; // Refetch every 30 seconds

const AIMCatalog: React.FC = () => {
  const { t } = useTranslation('models', { keyPrefix: 'aimCatalog' });
  const { toast } = useSystemToast();
  const { activeProject } = useProject();
  const queryClient = useQueryClient();
  const router = useRouter();

  const [filters, setFilters] = useState<ClientSideDataFilter<ParsedAIM>[]>([]);

  const [aggregatedAimForDeployment, setAggregatedAimForDeployment] = useState<
    AggregatedAIM | undefined
  >(undefined);
  const [serviceToUndeploy, setServiceToUndeploy] = useState<
    | {
        namespace: string;
        serviceId: string;
        displayName: string;
      }
    | undefined
  >(undefined);
  const [aimForConnect, setAimForConnect] = useState<ParsedAIM | undefined>(
    undefined,
  );

  const deployDisclosure = useDisclosure();
  const undeployDisclosure = useDisclosure();
  const connectDisclosure = useDisclosure();

  const {
    data: aims,
    isLoading: isAIMSLoading,
    refetch: refetchModels,
    error: modelsError,
  } = useQuery<ParsedAIM[]>({
    queryKey: ['project', activeProject, 'aim-catalog'],
    queryFn: () => getAimClusterModels(activeProject || undefined),
    refetchInterval: AIMS_REFETCH_INTERVAL,
    enabled: !!activeProject,
  });

  const memoizedAims = useMemo(() => {
    return aims || [];
  }, [aims]);

  const aggregatedAims = useMemo(() => {
    return transformToAggregatedAIMs(memoizedAims);
  }, [memoizedAims]);

  const filteredAggregatedAims = useMemo(() => {
    // Filter on the individual ParsedAIM level, then re-aggregate
    const filteredAims = getFilteredData(memoizedAims, filters);
    return transformToAggregatedAIMs(filteredAims);
  }, [memoizedAims, filters]);

  useEffect(() => {
    if (modelsError) {
      toast.error(
        t('actions.notifications.fetchError', {
          error: String(modelsError.message),
        }),
      );
    }
  }, [modelsError, toast, t]);

  const tags = useMemo(() => {
    const allTags = new Set<string>();
    aggregatedAims.forEach((aggregatedAim) => {
      aggregatedAim.parsedAIMs.forEach((aim) => {
        aim.tags?.forEach((tag) => {
          allTags.add(tag);
        });
      });
    });
    return Array.from(allTags).sort();
  }, [aggregatedAims]);

  const handleAimDeploy = useCallback(
    (aggregatedAim: AggregatedAIM) => {
      setAggregatedAimForDeployment(aggregatedAim);
      deployDisclosure.onOpen();
    },
    [deployDisclosure],
  );

  const handleOpenDetails = useCallback(
    (serviceId: string) => {
      router.push(`/aims/${serviceId}`);
    },
    [router],
  );

  const handleChatWithModel = useCallback((serviceId: string) => {
    window.open(`/chat?workload=${serviceId}`, '_blank');
  }, []);

  const handleConnectToModel = useCallback(
    (aim: ParsedAIM) => {
      setAimForConnect(aim);
      connectDisclosure.onOpen();
    },
    [connectDisclosure],
  );

  const handleConnectConfirm = useCallback(
    (aim: ParsedAIM) => {
      const serviceId = aim.deployedServices?.[0]?.id;
      if (serviceId) handleChatWithModel(serviceId);
      connectDisclosure.onClose();
      setAimForConnect(undefined);
    },
    [connectDisclosure, handleChatWithModel],
  );

  const handleConnectModalClose = useCallback(() => {
    connectDisclosure.onClose();
    setAimForConnect(undefined);
  }, [connectDisclosure]);

  const handleUndeploy = useCallback(
    (namespace: string, serviceId: string, displayName: string) => {
      setServiceToUndeploy({ namespace, serviceId, displayName });
      undeployDisclosure.onOpen();
    },
    [undeployDisclosure],
  );

  const handleConfirmUndeploy = useCallback(
    async (namespace: string, serviceId: string) => {
      try {
        await undeployAim(namespace, serviceId);
        toast.success(t('actions.notifications.deleteSuccess'));
        await refetchModels();
      } catch (error) {
        toast.error(
          t('actions.notifications.deleteError'),
          error as APIRequestError,
        );
      }
    },
    [toast, refetchModels, t],
  );

  const filterConfig = useMemo(
    () => ({
      search: {
        className: 'w-full',
        name: 'search',
        label: t('list.filter.search.placeholder'),
        placeholder: t('list.filter.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
      tags: {
        name: 'tags',
        icon: <IconTag />,
        label: t('list.filter.tag.placeholder'),
        placeholder: t('list.filter.tag.placeholder'),
        type: FilterComponentType.DROPDOWN,
        fields: tags.map((option) => ({
          label: option,
          key: option,
        })),
      },
      deploymentStatus: {
        name: 'deploymentStatus',
        icon: <IconRocket />,
        label: t('list.filter.deploymentStatus.placeholder'),
        placeholder: t('list.filter.deploymentStatus.placeholder'),
        type: FilterComponentType.DROPDOWN,
        fields: [
          {
            label: t('list.filter.deploymentStatus.deployed'),
            key: AIMWorkloadStatus.DEPLOYED,
          },
          {
            label: t('list.filter.deploymentStatus.notDeployed'),
            key: AIMWorkloadStatus.NOT_DEPLOYED,
          },
          {
            label: t('list.filter.deploymentStatus.pending'),
            key: AIMWorkloadStatus.PENDING,
          },
        ],
      },
    }),
    [t, tags],
  );

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<ParsedAIM>[] = [];

    if (filters?.search && filters.search.length > 0) {
      newFilters.push({
        compositeFields: [
          { field: 'title' },
          { field: 'imageVersion' },
          { field: 'description', path: 'short' },
        ],
        values: filters.search,
      });
    }

    if (filters?.deploymentStatus && filters.deploymentStatus.length > 0) {
      newFilters.push({
        field: 'workloadStatuses',
        values: filters.deploymentStatus,
        exact: true,
      });
    }

    if (filters?.tags && filters.tags.length > 0) {
      newFilters.push({
        field: 'tags',
        values: filters.tags,
      });
    }

    setFilters(newFilters);
  }, []);

  if (isAIMSLoading) {
    return (
      <div
        className="flex justify-center items-center h-64"
        data-testid="aim-catalog-loading"
      >
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  const isListEmpty =
    !filteredAggregatedAims || filteredAggregatedAims.length === 0;

  return (
    <div data-testid="aim-catalog">
      <p className="text-lg mb-4">{t('list.description')}</p>
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        onRefresh={refetchModels}
      />

      {isListEmpty ? (
        <p className="flex justify-center h-full items-center">
          {t('list.empty.description')}
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3 gap-6 mb-6">
          {filteredAggregatedAims.map((aggregatedAim) => (
            <AIMCard
              key={aggregatedAim.repository}
              aggregatedAim={aggregatedAim}
              onDeploy={() => handleAimDeploy(aggregatedAim)}
              onOpenDetails={handleOpenDetails}
              onChatWithModel={handleChatWithModel}
              onConnectToModel={handleConnectToModel}
              onUndeploy={handleUndeploy}
            />
          ))}
        </div>
      )}
      {aggregatedAimForDeployment && (
        <DeployAIMDrawer
          isOpen={deployDisclosure.isOpen}
          onClose={deployDisclosure.onClose}
          onDeploying={() => {
            queryClient.invalidateQueries({
              queryKey: ['project', activeProject, 'aim-catalog'],
            });
          }}
          aggregatedAim={aggregatedAimForDeployment}
        />
      )}
      <UndeployAIMModal
        isOpen={undeployDisclosure.isOpen}
        onOpenChange={undeployDisclosure.onOpenChange}
        onConfirmAction={handleConfirmUndeploy}
        serviceToUndeploy={serviceToUndeploy}
      />
      <AIMConnectModal
        isOpen={connectDisclosure.isOpen}
        onOpenChange={(isOpen) => !isOpen && handleConnectModalClose()}
        aim={aimForConnect}
        onConfirmAction={handleConnectConfirm}
      />
    </div>
  );
};

export default AIMCatalog;
