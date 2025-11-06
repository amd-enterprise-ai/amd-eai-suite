// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Button,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Selection,
  useDisclosure,
} from '@heroui/react';
import { IconChevronDown, IconCloudUpload } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import useSystemToast from '@/hooks/useSystemToast';

import {
  deleteDatasets,
  downloadDatasetById,
  getDatasets,
} from '@/services/app/datasets';

import { getFilteredData } from '@/utils/app/data-table';
import { getDatasetTypeVariants } from '@/utils/app/datasets';
import { authOptions } from '@/utils/server/auth';

import { TableColumns } from '@/types/data-table/clientside-table';
import { Dataset, DatasetType } from '@/types/datasets';
import { DatasetsTableField } from '@/types/enums/dataset-table-fields';
import { FilterComponentType } from '@/types/enums/filters';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { ActionButton } from '@/components/shared/Buttons';
import { DatasetUpload } from '@/components/features/datasets/DatasetUpload';
import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import {
  ChipDisplay,
  DateDisplay,
} from '@/components/shared/DataTable/CustomRenderers';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';

import { useProject } from '@/contexts/ProjectContext';

const DatasetsPage: React.FC = () => {
  const { toast } = useSystemToast();
  const { t } = useTranslation('datasets');
  const { activeProject } = useProject();
  const queryClient = useQueryClient();

  const { data, isLoading, refetch, dataUpdatedAt } = useQuery<Dataset[]>({
    queryKey: ['project', activeProject, 'datasets'],
    queryFn: () => getDatasets(activeProject!),
    enabled: !!activeProject,
  });

  const [filters, setFilters] = useState<ClientSideDataFilter<Dataset>[]>([]);
  const [datasetUploadVisible, setDatasetUploadVisible] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Selection>(new Set([]));
  const {
    isOpen: isDeleteConfirmOpen,
    onOpen: onDeleteConfirmOpen,
    onOpenChange: onDeleteConfirmOpenChange,
  } = useDisclosure();

  const typeFilterOptions = useMemo(
    () => [
      {
        name: t(`types.${DatasetType.Evaluation}`),
        type: DatasetType.Evaluation,
      },
      {
        name: t(`types.${DatasetType.Finetuning}`),
        type: DatasetType.Finetuning,
      },
    ],
    [t],
  );

  const columns: TableColumns<DatasetsTableField | null> = [
    {
      key: DatasetsTableField.TYPE,
      sortable: true,
    },
    {
      key: DatasetsTableField.NAME,
      sortable: true,
    },
    { key: DatasetsTableField.DESCRIPTION },
    { key: DatasetsTableField.CREATED_BY, sortable: true },
    { key: DatasetsTableField.CREATED_AT, sortable: true },
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

  const handleDownload = async (item: Dataset) => {
    try {
      await downloadDatasetById(item.id, activeProject!);
    } catch (_) {
      toast.error('Failed to download the dataset');
    }
  };

  const filteredDatasets = useMemo(() => {
    if (data) {
      return getFilteredData(data, filters);
    }
    return [];
  }, [data, filters]);

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
      onSuccess: () => {
        onDeleteConfirmOpenChange();
        queryClient.invalidateQueries({
          queryKey: ['project', activeProject, 'datasets'],
        });
        setSelectedKeys(new Set([]));
        refreshDatasets();
        toast.success(t('actions.delete.success'));
      },
      onError: () => {
        toast.error(t('actions.delete.error'));
      },
    });

  const handleDeleteSelected = useCallback(() => {
    let datasetIds: string[] = [];

    if (selectedKeys === 'all') {
      datasetIds = filteredDatasets.map((dataset) => dataset.id.toString());
    } else if (selectedKeys instanceof Set && selectedKeys.size > 0) {
      datasetIds = Array.from(selectedKeys) as string[];
    }
    if (datasetIds.length > 0) {
      handleDatasetDelete(datasetIds);
    }
  }, [handleDatasetDelete, filteredDatasets, selectedKeys]);

  const filterConfig = useMemo(
    () => ({
      type: {
        className: 'sm:w-[calc(100%-3.5rem)]',
        name: 'type',
        label: t('actions.datasetTypeFilter'),
        placeholder: t('actions.datasetTypeFilter'),
        type: FilterComponentType.SELECT,
        allowMultipleSelection: true,
        fields: typeFilterOptions.map((option) => ({
          label: option.name,
          key: option.type,
        })),
      },
    }),
    [t, typeFilterOptions],
  );

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<Dataset>[] = [];
    if (filters.type && filters.type.length > 0) {
      newFilters.push({
        field: 'type',
        values: filters.type,
      });
    }
    setFilters(newFilters);
  }, []);

  return (
    <div className="flex flex-col w-full">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        onRefresh={refreshDatasets}
        updatedTimestamp={dataUpdatedAt}
        isRefreshing={isLoading}
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
              <DropdownMenu aria-label="Actions">
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

      <ClientSideDataTable
        data={filteredDatasets}
        isSelectable
        selectedKeys={selectedKeys}
        onSelectionChange={handleSelectionChange}
        className="flex-1 overflow-y-auto"
        columns={columns}
        defaultSortByField={DatasetsTableField.NAME}
        translation={t}
        customRenderers={customRenderers}
        rowActions={actions}
        isLoading={isLoading}
        idKey={'id'}
      />
    </div>
  );
};

export async function getServerSideProps(context: any) {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  return {
    props: {
      ...(await serverSideTranslations(locale, ['common', 'datasets'])),
    },
  };
}

export default DatasetsPage;
