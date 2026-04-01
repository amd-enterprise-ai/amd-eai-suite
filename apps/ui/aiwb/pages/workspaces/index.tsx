// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Image, useDisclosure } from '@heroui/react';
import { IconAppWindow } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { useCallback, useMemo, useState } from 'react';
import { useRouter } from 'next/router';

import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { getFilteredData } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import { CatalogItem } from '@amdenterpriseai/types';
import { CatalogUsageScope } from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';

import { CatalogItemCard } from '@/components/features/catalog/CatalogItemCard';
import { DeployWorkloadDrawer } from '@/components/features/catalog/DeployWorkloadDrawer';
import { RelevantDocs } from '@amdenterpriseai/components';
import { ConfirmationModal } from '@amdenterpriseai/components';
import { ActionsToolbar } from '@amdenterpriseai/components';

import { useProject } from '@/contexts/ProjectContext';
import {
  deleteWorkload,
  listWorkloads,
  getCatalogItems,
} from '@/lib/app/workloads';

const WorkspacesPage: React.FC = () => {
  const router = useRouter();
  const { toast } = useSystemToast();
  const { t } = useTranslation('catalog');
  const { activeProject } = useProject();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ClientSideDataFilter<CatalogItem>[]>(
    [],
  );

  const { data: session } = useSession();

  const {
    data: catalogData,
    isLoading: isCatalogLoading,
    refetch: refetchCatalog,
    dataUpdatedAt: catalogUpdatedAt,
  } = useQuery({
    queryKey: ['project', activeProject, 'catalog', 'workspace'],
    queryFn: () => getCatalogItems(WorkloadType.WORKSPACE),
    enabled: !!activeProject,
    select: (c) =>
      c.map((item) => ({
        ...item,
        available: true,
      })),
  });
  const {
    data: workloadsData,
    isLoading: isWorkloadsLoading,
    refetch: refetchWorkloads,
    dataUpdatedAt: workloadsUpdatedAt,
  } = useQuery({
    queryKey: ['project', activeProject, 'workloads'],
    queryFn: async () => {
      if (!activeProject) return [];

      const response = await listWorkloads(activeProject, {
        type: [WorkloadType.WORKSPACE],
        status: [
          WorkloadStatus.RUNNING,
          WorkloadStatus.PENDING,
          WorkloadStatus.FAILED,
        ],
      });
      return response.data;
    },
    refetchInterval: 10000, // Refetch every 10 seconds
    enabled: !!activeProject,
  });

  const { mutate: deleteWorkloadMutation, isPending: isDeletePending } =
    useMutation({
      mutationFn: (id: string) => deleteWorkload(id, activeProject || ''),
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ['project', activeProject, 'workloads'],
        });
        toast.success(t('list.notifications.undeploySuccess'));
        onUndeployClose();
        setSelectedWorkload('');
      },
      onError: (error) => {
        toast.error(t('list.errors.undeployError'), error as APIRequestError);
      },
    });

  const dataUpdatedAt = catalogUpdatedAt || workloadsUpdatedAt;
  const isLoading = isCatalogLoading || isWorkloadsLoading;

  const categoryFilterOptions = [
    {
      name: t('categories.development'),
      id: 'development',
    },
    { name: t('categories.mlops'), id: 'mlops' },
    { name: t('categories.genai'), id: 'generative_ai' },
  ];

  const [selectedItem, setSelectedItem] = useState<CatalogItem>();
  const {
    isOpen: isDrawerOpen,
    onOpen: onDrawerOpen,
    onClose: onDrawerClose,
  } = useDisclosure();
  const handleItemClick = (item: CatalogItem) => {
    setSelectedItem(item);
    onDrawerOpen();
  };

  const [selectedWorkload, setSelectedWorkload] = useState<string>('');

  const isDeployed = (item: CatalogItem) => {
    return item.workloads?.some((w) => w.status === WorkloadStatus.RUNNING);
  };

  const isPending = (item: CatalogItem) => {
    return (
      isCatalogLoading ||
      isWorkloadsLoading ||
      item.workloads?.some((w) => w.status === WorkloadStatus.PENDING)
    );
  };

  const isFailed = (item: CatalogItem) =>
    item.workloads?.some((w) => w.status === WorkloadStatus.FAILED) ?? false;

  const {
    isOpen: isUndeployOpen,
    onOpen: onUndeployOpen,
    onClose: onUndeployClose,
  } = useDisclosure();

  const refreshCatalog = () => {
    refetchCatalog();
    refetchWorkloads();
  };

  const filteredCatalogItems = useMemo(() => {
    let filteredResults = catalogData ? [...catalogData] : [];

    // Check if workloadsData is available and add the workload status and resources
    // TODO/FIXME: It would probably be better to aggregate these in the backend
    if (workloadsData) {
      const statusFilter = [
        WorkloadStatus.RUNNING,
        WorkloadStatus.PENDING,
        WorkloadStatus.FAILED,
      ];
      filteredResults = filteredResults.map((item) => {
        // Workloads for this catalog item: running, pending, or failed, for current user or project scope
        const workloads = workloadsData.filter(
          (workload) =>
            workload.name.includes(item.name) &&
            statusFilter.includes(workload.status) &&
            (workload.createdBy === session?.user?.email ||
              item.usageScope === CatalogUsageScope.PROJECT),
        );

        return {
          ...item,
          workloadsCount: workloads.length,
          workloads,
          status: workloads[0]?.status,
          createdAt: workloads[0]?.createdAt,
          allocatedResources: workloads[0]?.allocatedResources,
        };
      });
    }

    filteredResults = getFilteredData(filteredResults, filters);

    return filteredResults;
  }, [catalogData, workloadsData, filters, session?.user?.email]);

  const launchWorkload = (item: CatalogItem) => {
    const workload = item.workloads?.find(
      (w) => w.status === WorkloadStatus.RUNNING,
    );

    if (!workload) {
      toast.error(t('list.errors.noRunningWorkload'));
      return;
    }

    const url =
      workload.endpoints?.external || workload.endpoints?.internal || '';
    window.open(url, '_blank');
  };

  const filterConfig = {
    search: {
      name: 'search',
      label: t('actions.search.label'),
      placeholder: t('actions.search.placeholder'),
      type: FilterComponentType.TEXT,
    },
    category: {
      name: 'category',
      label: t('actions.categoryFilter.label'),
      placeholder: t('actions.categoryFilter.label'),
      className: 'min-w-48',
      type: FilterComponentType.SELECT,
      allowMultipleSelection: true,
      fields: categoryFilterOptions.map((option) => ({
        label: option.name,
        key: option.id,
      })),
    },
  };

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<CatalogItem>[] = [];

    if (filters?.search) {
      newFilters.push({
        field: 'displayName',
        values: filters.search,
      });
    }

    if (filters?.category && filters.category.length > 0) {
      newFilters.push({
        field: 'category',
        values: filters.category,
      });
    }

    setFilters(newFilters);
  }, []);

  return (
    <>
      <div className="min-h-full flex flex-col w-full">
        <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
          <ActionsToolbar
            filterConfig={filterConfig}
            onFilterChange={handleFilterChange}
            onRefresh={refreshCatalog}
            updatedTimestamp={dataUpdatedAt}
            isRefreshing={isLoading}
          />

          <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-6 pl-2 pr-2 mb-6 w-full">
            {filteredCatalogItems.map((item: CatalogItem) => (
              <CatalogItemCard
                item={item}
                onOpenWorkloadDetails={(id) => router.push(`/workloads/${id}`)}
                primaryAction={{
                  key: 'deploy',
                  label: t('list.actions.deploy'),
                  onPress: handleItemClick,
                }}
                secondaryActionColor="danger"
                secondaryAction={
                  isDeployed(item)
                    ? {
                        key: 'undeploy',
                        label: t('list.actions.undeploy'),
                        onPress: () => {
                          setSelectedWorkload(item.workloads?.[0]?.id ?? '');
                          onUndeployOpen();
                        },
                      }
                    : isFailed(item)
                      ? {
                          key: 'deleteFailed',
                          label: t('list.actions.deleteFailedWorkload'),
                          onPress: () => {
                            const failed = item.workloads?.find(
                              (w) => w.status === WorkloadStatus.FAILED,
                            );
                            setSelectedWorkload(failed?.id ?? '');
                            onUndeployOpen();
                          },
                        }
                      : undefined
                }
                key={item.id}
                pendingLabel={t('list.actions.pending')}
                readyAction={{
                  key: 'launch',
                  label: t('list.actions.launch'),
                  onPress: (item: CatalogItem) => {
                    launchWorkload(item);
                  },
                }}
                isDeployed={isDeployed(item)}
                isPending={isPending(item)}
                isFailed={isFailed(item)}
                iconComponent={
                  item.featuredImage ? (
                    <Image
                      alt="workload icon"
                      height={40}
                      radius="md"
                      src={item.featuredImage}
                      width={40}
                    />
                  ) : (
                    <IconAppWindow size={32} />
                  )
                }
                minHeaderHeight="4.5em"
                iconTopGap
              />
            ))}
          </div>
        </div>

        <RelevantDocs page="workspaces" />
      </div>

      {selectedItem && (
        <DeployWorkloadDrawer
          isModelDeployment={false}
          isOpen={isDrawerOpen}
          onClose={onDrawerClose}
          catalogItem={selectedItem}
          onDeploying={() =>
            queryClient.invalidateQueries({
              queryKey: ['project', activeProject, 'workloads'],
            })
          }
          onDeployed={() => {
            queryClient.invalidateQueries({
              queryKey: ['project', activeProject, 'workloads'],
            });
          }}
        />
      )}

      <ConfirmationModal
        confirmationButtonColor="danger"
        title={t('undeployModal.title')}
        description={t('undeployModal.description')}
        isOpen={isUndeployOpen}
        loading={isDeletePending}
        onConfirm={() => deleteWorkloadMutation(selectedWorkload)}
        onClose={onUndeployClose}
      />
    </>
  );
};

export async function getServerSideProps(context: any) {
  const { locale } = context;

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'common',
        'catalog',
        'sharedComponents',
      ])),
    },
  };
}

export default WorkspacesPage;
