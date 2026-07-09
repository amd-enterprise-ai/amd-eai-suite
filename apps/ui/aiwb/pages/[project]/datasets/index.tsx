// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  type Selection,
  Button,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  ActionButton,
  RelevantDocs,
  AiwbDocsPage,
  aiwbDocumentationMapping,
  ConfirmationModal,
  ServerSideDataTable,
  ChipDisplay,
  DateDisplay,
  ActionsToolbar,
} from '@amdenterpriseai/components';
import {
  useDebouncedCallback,
  useOverlayState,
  useSystemToast,
} from '@amdenterpriseai/hooks';
import { IconChevronDown, IconCloudUpload } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import {
  DOCS_WORKBENCH_BASE,
  WithDocumentationLink,
} from '@amdenterpriseai/utils/app';
import {
  deleteDatasets,
  downloadDatasetById,
  getDatasetTypeVariants,
  listDatasets,
} from '@/lib/app/datasets';
import { PaginatedList } from '@/types/pagination';

import { TableColumns } from '@amdenterpriseai/types';
import { CollectionRequestParams } from '@amdenterpriseai/types';
import { FilterParams } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';
import { Dataset, DatasetType } from '@/types/datasets';
import { DatasetsTableField } from '@/types/enums/dataset-table-fields';
import { FilterComponentType } from '@amdenterpriseai/types';
import { FilterValueMap } from '@amdenterpriseai/types';
import { DatasetUpload } from '@/components/features/datasets/DatasetUpload';
import {
  DatasetDownloadIndicator,
  DownloadStatus,
} from '@/components/features/datasets/DatasetDownloadIndicator';

import { useProject } from '@/contexts/ProjectContext';

const API_REQUEST_DEFAULTS: CollectionRequestParams<Dataset> = {
  page: 1,
  pageSize: 10,
  sort: [
    {
      field: 'createdAt' as keyof Dataset,
      direction: SortDirection.DESC,
    },
  ],
  filter: [],
};

const DatasetsPage: React.FC & WithDocumentationLink = () => {
  const { toast } = useSystemToast();
  const { t } = useTranslation('datasets');
  const { activeProject } = useProject();
  const queryClient = useQueryClient();

  const [tableParams, setTableParams] =
    useState<CollectionRequestParams<Dataset>>(API_REQUEST_DEFAULTS);
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<
    DatasetType | undefined
  >(undefined);
  const [datasetUploadVisible, setDatasetUploadVisible] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Selection>(new Set([]));
  const [downloadStatus, setDownloadStatus] = useState<DownloadStatus | null>(
    null,
  );
  // Incremented on each new download and on dismiss so in-flight handlers
  // can detect that the user has already dismissed or started a newer download.
  const downloadIdRef = useRef(0);
  const {
    isOpen: isDeleteConfirmOpen,
    onOpen: onDeleteConfirmOpen,
    onOpenChange: onDeleteConfirmOpenChange,
  } = useOverlayState();

  const fetchParams = useMemo(() => {
    return {
      page: tableParams.page,
      pageSize: tableParams.pageSize,
      type: selectedTypeFilter,
    };
  }, [tableParams.page, tableParams.pageSize, selectedTypeFilter]);

  const {
    data: paginatedDatasets,
    isLoading,
    isFetching,
    refetch,
    dataUpdatedAt,
  } = useQuery<PaginatedList<Dataset>>({
    queryKey: ['project', activeProject, 'datasets', fetchParams],
    queryFn: () => listDatasets(activeProject!, fetchParams),
    enabled: !!activeProject,
  });

  const data = paginatedDatasets?.data ?? [];
  const total = paginatedDatasets?.pagination.total ?? 0;

  const typeFilterOptions = useMemo(
    () => [
      {
        name: t(`types.${DatasetType.Finetuning}`),
        type: DatasetType.Finetuning,
      },
    ],
    [t],
  );

  // Sort is intentionally disabled: the datasets list endpoint does not accept
  // sort params (no SortCondition on ListDatasetsQuery), so a sortable header
  // would just toggle a sort indicator without re-fetching ordered data.
  const columns: TableColumns<DatasetsTableField | null> = [
    { key: DatasetsTableField.TYPE },
    { key: DatasetsTableField.NAME },
    { key: DatasetsTableField.DESCRIPTION },
    { key: DatasetsTableField.CREATED_BY },
    { key: DatasetsTableField.CREATED_AT },
  ];

  const actions = [
    {
      key: 'download',
      aria: 'Download',
      className: '',
      color: 'default',
      onPress: (item: Dataset) => {
        handleDownload(item);
      },
      label: t('list.actions.download.label'),
    },
    {
      key: 'delete',
      className: 'text-danger',
      color: 'danger',
      onPress: (item: Dataset) => {
        handleDelete(item.id);
      },
      label: t('list.actions.delete.label'),
    },
  ];

  const handleSelectionChange = (keys: Selection) => {
    setSelectedKeys(keys);
  };

  const handleDelete = useCallback(
    (id: string) => {
      setSelectedKeys(new Set([id]));
      onDeleteConfirmOpenChange();
    },
    [onDeleteConfirmOpenChange],
  );

  const refreshDatasets = () => {
    refetch();
  };

  useEffect(() => {
    if (downloadStatus === DownloadStatus.DONE) {
      const timer = setTimeout(() => setDownloadStatus(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [downloadStatus]);

  const handleDownload = async (item: Dataset) => {
    const id = ++downloadIdRef.current;
    setDownloadStatus(DownloadStatus.PREPARING);
    try {
      await downloadDatasetById(item.id, activeProject!);
      if (downloadIdRef.current === id) {
        setDownloadStatus(DownloadStatus.DONE);
      }
    } catch (_) {
      if (downloadIdRef.current === id) {
        setDownloadStatus(null);
        toast.error(t('download.error'));
      }
    }
  };

  const customRenderers: Partial<
    Record<DatasetsTableField, (item: Dataset) => React.ReactNode | string>
  > = {
    [DatasetsTableField.TYPE]: (item) => (
      <ChipDisplay
        type={item[DatasetsTableField.TYPE] as DatasetType}
        variants={getDatasetTypeVariants(t)}
      />
    ),
    [DatasetsTableField.CREATED_AT]: (item) => (
      <DateDisplay date={item[DatasetsTableField.CREATED_AT]} />
    ),
  };

  const { mutate: handleDatasetDelete, isPending: isDeletingDatasets } =
    useMutation({
      mutationFn: (ids: string[]) => deleteDatasets(ids, activeProject!),
      onSuccess: (result) => {
        onDeleteConfirmOpenChange();
        queryClient.invalidateQueries({
          queryKey: ['project', activeProject, 'datasets'],
        });
        setSelectedKeys(new Set([]));
        refreshDatasets();
        if (result.failed.length === 0) {
          toast.success(t('actions.delete.success'));
        } else if (result.succeededIds.length === 0) {
          toast.error(t('actions.delete.error'));
        } else {
          toast.error(
            t('actions.delete.partialError', { count: result.failed.length }),
          );
        }
      },
      onError: () => {
        toast.error(t('actions.delete.error'));
      },
    });

  const handleDeleteSelected = useCallback(() => {
    let datasetIds: string[] = [];

    // Server-side pagination: "select all" refers to rows on the current page.
    // Bulk operations therefore target the visible page only — the backend does
    // not expose an "all matching" delete contract.
    if (selectedKeys === 'all') {
      datasetIds = data.map((dataset) => dataset.id.toString());
    } else if (selectedKeys instanceof Set && selectedKeys.size > 0) {
      datasetIds = Array.from(selectedKeys) as string[];
    }
    if (datasetIds.length > 0) {
      handleDatasetDelete(datasetIds);
    }
  }, [handleDatasetDelete, data, selectedKeys]);

  const filterConfig = useMemo(
    () => ({
      type: {
        className: 'sm:w-[calc(100%-3.5rem)]',
        name: 'type',
        label: t('actions.datasetTypeFilter'),
        placeholder: t('actions.datasetTypeFilter'),
        type: FilterComponentType.SELECT,
        // EAI-6577: backend supports a single exact `type` match only.
        // Constrain UI to single-select to keep filter semantics honest.
        allowMultipleSelection: false,
        fields: typeFilterOptions.map((option) => ({
          label: option.name,
          key: option.type,
        })),
      },
    }),
    [t, typeFilterOptions],
  );

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const next = filters.type?.[0] as DatasetType | undefined;
    setSelectedTypeFilter(next);
    setSelectedKeys(new Set([]));
    // Reset to page 1 immediately so the next fetch uses the new filter on
    // page 1, not the old page number. ServerSideDataTable also resets via
    // its filters effect, but this avoids the brief window where a stale
    // page request is issued before that effect runs.
    setTableParams((prev) => ({ ...prev, page: 1 }));
  }, []);

  // Surface the type filter to ServerSideDataTable so its built-in
  // reset-to-page-1 effect fires when the user changes filters. Without this,
  // a filter change while on page > 1 would refetch the same page with the
  // new filter — likely empty — while the pagination control still shows the
  // old page.
  const tableFilters = useMemo<FilterParams<Dataset>[]>(
    () =>
      selectedTypeFilter
        ? [{ fields: ['type'], values: [selectedTypeFilter] }]
        : [],
    [selectedTypeFilter],
  );

  const handleTableParamsChange = useDebouncedCallback(
    (params: CollectionRequestParams<Dataset>) => {
      setTableParams(params);
    },
    100,
  );

  return (
    <div className="min-h-full flex flex-col w-full">
      <div className="flex-1 flex flex-col min-h-0">
        <ActionsToolbar
          filterConfig={filterConfig}
          onFilterChange={handleFilterChange}
          onRefresh={refreshDatasets}
          updatedTimestamp={dataUpdatedAt}
          isRefreshing={isLoading || isFetching}
          endContent={
            <div className="flex gap-3 items-center">
              <Dropdown>
                <DropdownTrigger>
                  <Button
                    isDisabled={
                      selectedKeys === 'all'
                        ? false
                        : selectedKeys instanceof Set
                          ? selectedKeys.size === 0
                          : true
                    }
                    endContent={<IconChevronDown className="text-small" />}
                    variant="flat"
                    radius="md"
                  >
                    {t('actions.actionsDropdown')}
                  </Button>
                </DropdownTrigger>
                <DropdownMenu aria-label={t('actions.actionsDropdown')}>
                  <DropdownItem
                    key="delete"
                    className="text-danger"
                    color="danger"
                    onPress={onDeleteConfirmOpen}
                  >
                    {t('actions.delete.label')}
                  </DropdownItem>
                </DropdownMenu>
              </Dropdown>
              <ActionButton
                primary
                aria-label={t('actions.upload') || ''}
                className="hidden md:flex"
                icon={<IconCloudUpload size={16} stroke={2} />}
                isDisabled={isLoading}
                onPress={() => setDatasetUploadVisible(true)}
              >
                {t('actions.upload')}
              </ActionButton>
              <ActionButton
                primary
                data-testid="upload-dataset-button"
                className="flex md:hidden"
                icon={<IconCloudUpload size={16} stroke={2} />}
                isDisabled={isLoading}
                onPress={() => setDatasetUploadVisible(true)}
              ></ActionButton>

              {datasetUploadVisible && (
                <DatasetUpload
                  isOpen={datasetUploadVisible}
                  refresh={() => refreshDatasets()}
                  onClose={() => setDatasetUploadVisible(false)}
                />
              )}
              <ConfirmationModal
                description={t('actions.delete.confirm.description')}
                title={t('actions.delete.confirm.title')}
                isOpen={isDeleteConfirmOpen}
                loading={isDeletingDatasets}
                onConfirm={handleDeleteSelected}
                onClose={onDeleteConfirmOpenChange}
                confirmationButtonColor="danger"
              />
            </div>
          }
        />

        <ServerSideDataTable
          filters={tableFilters}
          data={data}
          total={total}
          handleDataRequest={handleTableParamsChange}
          isSelectable
          selectedKeys={selectedKeys}
          onSelectionChange={handleSelectionChange}
          className="flex-1 overflow-y-auto"
          columns={columns}
          defaultSortByField={DatasetsTableField.CREATED_AT}
          defaultSortDirection={SortDirection.DESC}
          translation={t}
          customRenderers={customRenderers}
          rowActions={actions}
          isLoading={isLoading}
          isFetching={isFetching}
          idKey={'id'}
        />
      </div>
      <RelevantDocs docs={aiwbDocumentationMapping[AiwbDocsPage.DATASETS]} />
      {downloadStatus && (
        <DatasetDownloadIndicator
          status={downloadStatus}
          onDismiss={() => {
            downloadIdRef.current++;
            setDownloadStatus(null);
          }}
        />
      )}
    </div>
  );
};

export async function getServerSideProps(context: any) {
  const { locale } = context;

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'common',
        'datasets',
        'sharedComponents',
      ])),
    },
  };
}

export default DatasetsPage;

DatasetsPage.documentationLink = `${DOCS_WORKBENCH_BASE}/training/datasets.html`;
