// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Image, Tab, Tabs, useDisclosure } from '@heroui/react';
import {
  IconAppWindow,
  IconExternalLink,
  IconLayoutGrid,
  IconRocket,
  IconRocketOff,
  IconTable,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { useCallback, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import useSystemToast from '@/hooks/useSystemToast';

import { getCatalogItems } from '@/services/app/catalog';
import { deleteWorkload, listWorkloads } from '@/services/app/workloads';

import { getFilteredData } from '@/utils/app/data-table';
import { APIRequestError } from '@/utils/app/errors';
import { displayMegabytesInGigabytes } from '@/utils/app/memory';
import getWorkloadStatusVariants from '@/utils/app/workloads-status-variants';

import { CatalogItem, CatalogTableItem } from '@/types/catalog';
import { ActionItem, TableColumn } from '@/types/data-table/clientside-table';
import { CatalogUsageScope } from '@/types/enums/catalog';
import { FilterComponentType } from '@/types/enums/filters';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { WorkloadsTableFields } from '@/types/enums/workloads-table-fields';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';

import { CatalogItemCard } from '@/components/features/catalog/CatalogItemCard';
import { DeployWorkloadDrawer } from '@/components/features/catalog/DeployWorkloadDrawer';
import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import {
  DateDisplay,
  NoDataDisplay,
  StatusBadgeDisplay,
  TranslationDisplay,
} from '@/components/shared/DataTable/CustomRenderers';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';

import { useProject } from '@/contexts/ProjectContext';

const WorkspacesPage: React.FC = () => {
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
    queryKey: ['project', activeProject, 'catalog'],
    queryFn: () => getCatalogItems(),
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
      return await listWorkloads(activeProject!, {
        withResources: true,
        type: [WorkloadType.WORKSPACE],
        status: [WorkloadStatus.RUNNING, WorkloadStatus.PENDING],
      });
    },
    refetchInterval: 10000, // Refetch every 10 seconds
    enabled: !!activeProject,
  });

  const { mutate: deleteWorkloadMutation, isPending: isDeletePending } =
    useMutation({
      mutationFn: deleteWorkload,
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

  const [displayStyle, setDisplayStyle] = useState<string>('grid');
  const displayStyleOptions = [
    { type: 'grid', icon: <IconLayoutGrid size={16} /> },
    { type: 'list', icon: <IconTable size={16} /> },
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

  const {
    isOpen: isUndeployOpen,
    onOpen: onUndeployOpen,
    onClose: onUndeployClose,
  } = useDisclosure();

  const columns: TableColumn<WorkloadsTableFields>[] = [
    { key: WorkloadsTableFields.DISPLAY_NAME, sortable: true },
    { key: WorkloadsTableFields.STATUS, sortable: true },
    { key: WorkloadsTableFields.SHORT_DESCRIPTION },
    { key: WorkloadsTableFields.VRAM, sortable: true },
    { key: WorkloadsTableFields.GPU, sortable: true },
    { key: WorkloadsTableFields.CREATED_AT, sortable: true },
  ];

  const customRenderers: Partial<
    Record<
      WorkloadsTableFields,
      (item: CatalogItem) => React.ReactNode | string
    >
  > = {
    [WorkloadsTableFields.VRAM]: (item: CatalogTableItem) => {
      return !item.allocatedResources?.vram ? (
        <NoDataDisplay />
      ) : (
        <TranslationDisplay
          ns="catalog"
          tKey="list.valueTemplates.vram"
          value={displayMegabytesInGigabytes(item.allocatedResources?.vram)}
        />
      );
    },
    [WorkloadsTableFields.GPU]: (item: CatalogTableItem) => {
      return !item.allocatedResources?.gpuCount ? (
        <NoDataDisplay />
      ) : (
        <TranslationDisplay
          ns="catalog"
          tKey="list.valueTemplates.gpu"
          value={item.allocatedResources?.gpuCount}
        />
      );
    },
    [WorkloadsTableFields.CREATED_AT]: (item: CatalogTableItem) => {
      return !item.createdAt ? (
        <NoDataDisplay />
      ) : (
        <DateDisplay date={item.createdAt} />
      );
    },
    [WorkloadsTableFields.STATUS]: (item: CatalogTableItem) => {
      return !item.status ? (
        <NoDataDisplay />
      ) : (
        <StatusBadgeDisplay
          type={item[WorkloadsTableFields.STATUS]}
          variants={getWorkloadStatusVariants(t)}
        />
      );
    },
  };

  const rowActions = (item: CatalogItem) => {
    let actionsList: ActionItem<CatalogItem>[] = [];

    if (!item.workloads || item.workloads.length === 0) {
      actionsList.push({
        key: 'deploy',
        label: t('list.actions.deploy'),
        startContent: <IconRocket />,
        onPress: (item) => {
          setSelectedItem(item);
          onDrawerOpen();
        },
      });
    }

    if (item.workloads?.some((w) => w.status === WorkloadStatus.RUNNING)) {
      actionsList.push({
        key: 'launch',
        label: t('list.actions.launch'),
        isDisabled: isPending(item),
        startContent: <IconExternalLink />,
        onPress: (item: CatalogItem) => {
          launchWorkload(item);
        },
      });
      actionsList.push({
        key: 'undeploy',
        label: t('list.actions.undeploy'),
        isDisabled: isPending(item),
        color: 'danger',
        startContent: <IconRocketOff />,
        onPress: (item: CatalogItem) => {
          setSelectedWorkload(item.workloads?.[0]?.id);
          onUndeployOpen();
        },
      });
    }

    if (item.workloads?.some((w) => w.status === WorkloadStatus.PENDING)) {
      actionsList.push({
        key: 'undeploy',
        label: t('list.actions.undeploy'),
        color: 'danger',
        startContent: <IconRocketOff />,
        onPress: (item: CatalogItem) => {
          setSelectedWorkload(item.workloads?.[0]?.id);
          onUndeployOpen();
        },
      });
    }

    return actionsList;
  };

  const refreshCatalog = () => {
    refetchCatalog();
    refetchWorkloads();
  };

  const filteredCatalogItems = useMemo(() => {
    let filteredResults = catalogData ? [...catalogData] : [];

    // Check if workloadsData is available and add the workload status and resources
    // TODO/FIXME: It would probably be better to aggregate these in the backend
    if (workloadsData) {
      filteredResults = filteredResults.map((item) => {
        // Get active workloads submitted by the current user
        const workloads = workloadsData.filter(
          (workload) =>
            workload.name.includes(item.name) &&
            (workload.status === WorkloadStatus.RUNNING ||
              workload.status === WorkloadStatus.PENDING) &&
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

    const url = workload.output?.externalHost || workload.output?.host || '';
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
      label: t('actions.category.label'),
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

    if (filters?.category) {
      newFilters.push({
        field: 'category',
        values: filters.category,
      });
    }

    setFilters(newFilters);
  }, []);

  return (
    <>
      <div className="flex flex-col w-full overflow-y-auto">
        <ActionsToolbar
          filterConfig={filterConfig}
          onFilterChange={handleFilterChange}
          onRefresh={refreshCatalog}
          updatedTimestamp={dataUpdatedAt}
          isRefreshing={isLoading}
          extraContent={
            <Tabs
              aria-label={t('actions.displayStyle.label')}
              color="default"
              selectedKey={displayStyle}
              onSelectionChange={(key) => setDisplayStyle(key as string)}
              size="md"
              data-testid="catalog-display-style-selector"
            >
              {displayStyleOptions.map((item) => (
                <Tab
                  key={item.type}
                  title={
                    <div className="flex items-center space-x-2">
                      {item.icon}
                      <span>{t(`displayStyle.${item.type}`)}</span>
                    </div>
                  }
                  data-testid={`display-option-${item.type}`}
                  aria-label={t(`displayStyle.${item.type}`)}
                ></Tab>
              ))}
            </Tabs>
          }
        />

        {displayStyle.includes('list') && (
          <ClientSideDataTable
            data={filteredCatalogItems}
            className="flex-1 overflow-y-auto"
            columns={columns}
            customRenderers={customRenderers}
            defaultSortByField={'name'}
            translation={t}
            isLoading={isCatalogLoading || isWorkloadsLoading}
            idKey={'id'}
            data-testid="catalog-list"
            onRowPressed={(id) => {
              const item = filteredCatalogItems.find((item) => item.id === id);
              if (item) {
                handleItemClick(item);
              }
            }}
            rowActions={rowActions}
          />
        )}
        {displayStyle.includes('grid') && (
          <div className="flex flex-wrap items-stretch gap-6 pl-2 pr-2 mb-6">
            {filteredCatalogItems.map((item: CatalogItem) => (
              <CatalogItemCard
                item={item}
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
                          setSelectedWorkload(item.workloads?.[0]?.id);
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
        )}
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
      ...(await serverSideTranslations(locale, ['common', 'catalog'])),
    },
  };
}

export default WorkspacesPage;
