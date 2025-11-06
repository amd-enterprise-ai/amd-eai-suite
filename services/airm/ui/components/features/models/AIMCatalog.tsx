// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Spinner, useDisclosure } from '@heroui/react';
import { IconRocket, IconTag } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { useTranslation, Trans } from 'next-i18next';
import { useRouter } from 'next/router';

import useSystemToast from '@/hooks/useSystemToast';

import { getAims, undeployAim } from '@/services/app/aims';

import { getFilteredData } from '@/utils/app/data-table';

import { FilterComponentType } from '@/types/enums/filters';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { Aim, AimWorkloadStatus } from '@/types/aims';

import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';
import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';

import { AIMCard } from './AIMCard';
import AIMConnectModal from './AIMConnectModal';
import { DeployAIMDrawer } from './DeployAIMDrawer';

import { useProject } from '@/contexts/ProjectContext';

const AIMS_REFETCH_INTERVAL = 30000; // Refetch every 30 seconds

const AIMCatalog: React.FC = () => {
  const router = useRouter();
  const { t } = useTranslation('models', { keyPrefix: 'aimCatalog' });
  const { toast } = useSystemToast();
  const { activeProject } = useProject();
  const queryClient = useQueryClient();

  const [filters, setFilters] = useState<ClientSideDataFilter<Aim>[]>([]);

  const [currentAim, setCurrentAim] = useState<Aim | undefined>(undefined);
  const [aimForDeployment, setAimForDeployment] = useState<Aim | undefined>(
    undefined,
  );

  const connectModalDisclosure = useDisclosure();
  const undeployAimDisclosure = useDisclosure();
  const deployDisclosure = useDisclosure();

  const {
    data: aims,
    isLoading: isAIMSLoading,
    refetch: refetchModels,
    error: modelsError,
  } = useQuery<Aim[]>({
    queryKey: ['project', activeProject, 'aim-catalog'],
    queryFn: () => getAims(activeProject!),
    refetchInterval: AIMS_REFETCH_INTERVAL,
    enabled: !!activeProject,
  });

  const undeployAimMutation = useMutation({
    mutationFn: ({ projectId, aimId }: { projectId: string; aimId: string }) =>
      undeployAim(aimId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'aim-catalog'],
      });
      toast.success(t('actions.notifications.deleteSuccess'));
      undeployAimDisclosure.onClose();
    },
    onError: (_) => {
      toast.error(t('actions.notifications.deleteError'));
    },
  });

  const memoizedAims = useMemo(() => aims || [], [aims]);

  const filteredModels = useMemo(() => {
    const filtered = getFilteredData(memoizedAims, filters);

    return filtered;
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
    memoizedAims.forEach((model) => {
      model.tags?.forEach((tag) => {
        allTags.add(tag);
      });
    });
    return Array.from(allTags);
  }, [memoizedAims]);

  const handleConnectConfirm = useCallback(
    (aim: Aim) => {
      const workloadId = aim.workload?.id;
      const query = workloadId ? `?workload=${workloadId}` : '';
      router.push(`/chat${query}`);
    },
    [router],
  );

  const handleAimDeploy = useCallback(
    (aim: Aim) => {
      setAimForDeployment(aim);
      deployDisclosure.onOpen();
    },
    [deployDisclosure],
  );

  const handleAimUndeploy = useCallback(
    (aim: Aim) => {
      if (aim.workload) {
        setCurrentAim(aim);
        undeployAimDisclosure.onOpen();
      }
    },
    [undeployAimDisclosure],
  );

  const handleAimConnect = useCallback(
    (aim: Aim) => {
      setCurrentAim(aim);
      connectModalDisclosure.onOpen();
    },
    [connectModalDisclosure],
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
            key: AimWorkloadStatus.DEPLOYED,
          },
          {
            label: t('list.filter.deploymentStatus.notDeployed'),
            key: AimWorkloadStatus.NOT_DEPLOYED,
          },
          {
            label: t('list.filter.deploymentStatus.pending'),
            key: AimWorkloadStatus.PENDING,
          },
        ],
      },
    }),
    [t, tags],
  );

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<Aim>[] = [];
    if (filters?.search) {
      newFilters.push({
        compositeFields: [
          { field: 'title' },
          { field: 'imageTag' },
          { field: 'description', path: 'short' },
        ],
        values: filters.search,
      });
    }
    if (filters?.deploymentStatus) {
      // Store deployment status as a special filter marker with required values property
      newFilters.push({
        field: 'workloadStatus',
        values: filters.deploymentStatus,
        exact: true, // Use exact matching for enum values
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

  return (
    <div data-testid="aim-catalog">
      <p className="text-lg mb-4">{t('list.description')}</p>

      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        onRefresh={refetchModels}
      />

      {isAIMSLoading && (
        <div
          className="flex justify-center items-center h-64"
          data-testid="aim-catalog-loading"
        >
          <Spinner size="lg" color="primary" />
        </div>
      )}

      {!isAIMSLoading && !!aims && (
        <div className="flex flex-wrap items-stretch gap-6 mb-6">
          {filteredModels.map((aim) => (
            <AIMCard
              key={aim.id}
              item={aim}
              onDeploy={handleAimDeploy}
              onUndeploy={handleAimUndeploy}
              onConnect={handleAimConnect}
            />
          ))}
        </div>
      )}

      {!isAIMSLoading && (!filteredModels || filteredModels.length === 0) && (
        <p className="flex justify-center h-full items-center">
          {t('list.empty.description')}
        </p>
      )}

      <AIMConnectModal
        isOpen={connectModalDisclosure.isOpen}
        onOpenChange={connectModalDisclosure.onOpenChange}
        aim={currentAim}
        onConfirmAction={handleConnectConfirm}
      />

      <ConfirmationModal
        isOpen={undeployAimDisclosure.isOpen}
        onConfirm={() =>
          undeployAimMutation.mutate({
            projectId: activeProject!,
            aimId: currentAim!.id,
          })
        }
        description={
          <Trans parent="span">
            {t('actions.undeploy.confirmation.description', {
              name: currentAim?.title || '',
            })}
          </Trans>
        }
        title={t('actions.undeploy.confirmation.title')}
        loading={undeployAimMutation.isPending}
        onClose={undeployAimDisclosure.onClose}
        confirmationButtonColor="danger"
      />

      {aimForDeployment && (
        <DeployAIMDrawer
          isOpen={deployDisclosure.isOpen}
          onClose={deployDisclosure.onClose}
          onDeploying={() => {
            queryClient.invalidateQueries({
              queryKey: ['project', activeProject, 'aim-catalog'],
            });
          }}
          aim={aimForDeployment}
        />
      )}
    </div>
  );
};

export default AIMCatalog;
