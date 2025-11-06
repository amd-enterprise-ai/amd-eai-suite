// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Chip } from '@heroui/react';
import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { fetchProjectStorages } from '@/services/app/storages';

import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';
import { getFilteredData } from '@/utils/app/data-table';
import { doesProjectStorageDataNeedToBeRefreshed } from '@/utils/app/storages';
import { displayTimestamp } from '@/utils/app/strings';

import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { SecretsTableField } from '@/types/enums/secrets-table-field';
import { StoragesTableField } from '@/types/enums/storages';
import { ClientSideDataFilter } from '@/types/filters';
import {
  ProjectStorageWithParentStorage,
  ProjectStoragesResponse,
} from '@/types/storages';

import { ClientSideDataTable } from '@/components/shared/DataTable';

import { ProjectStorageStatus } from '../storages';

interface Props {
  filters?: ClientSideDataFilter<ProjectStorageWithParentStorage>[];
  actions?: ActionItem<ProjectStorageWithParentStorage>[];
  projectId: string;
  projectStorages: ProjectStorageWithParentStorage[];
}

export const ProjectStoragesTable: React.FC<Props> = ({
  filters,
  actions,
  projectId,
  projectStorages,
}) => {
  const { t } = useTranslation('storages');

  const { data: projectStoragesData, isLoading: isSecretsLoading } =
    useQuery<ProjectStoragesResponse>({
      queryKey: ['project-storages', projectId],
      queryFn: () => fetchProjectStorages(projectId),
      initialData: {
        projectStorages,
      },
      refetchInterval: (query) => {
        return !query.state.data ||
          doesProjectStorageDataNeedToBeRefreshed(
            query.state.data.projectStorages,
          )
          ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
          : false;
      },
    });

  const filteredData = useMemo(() => {
    const data = projectStoragesData.projectStorages;
    return getFilteredData(data, filters);
  }, [projectStoragesData, filters]);

  const columns: TableColumns<StoragesTableField | null> = [
    {
      key: StoragesTableField.NAME,
      sortable: true,
    },
    {
      key: StoragesTableField.TYPE,
      sortable: true,
    },
    {
      key: StoragesTableField.STATUS,
      sortable: true,
    },
    {
      key: StoragesTableField.CREATED_AT,
      sortable: true,
    },
    {
      key: StoragesTableField.CREATED_BY,
      sortable: true,
    },
  ];
  const customRenderers = useMemo(
    () => ({
      [StoragesTableField.NAME]: (item: ProjectStorageWithParentStorage) => (
        <span>{item.storage.name}</span>
      ),
      [StoragesTableField.TYPE]: (item: ProjectStorageWithParentStorage) => {
        return <Chip>{t(`storageType.${item.storage.type}`)}</Chip>;
      },
      [StoragesTableField.STATUS]: (item: ProjectStorageWithParentStorage) => (
        <ProjectStorageStatus
          status={item.status}
          statusReason={item.statusReason}
        />
      ),
      [StoragesTableField.SCOPE]: (item: ProjectStorageWithParentStorage) => {
        return t(`storageScope.${item.scope}`); // TODO: Update to use item.scope when avaliable
      },
      [StoragesTableField.CREATED_AT]: (
        item: ProjectStorageWithParentStorage,
      ) => displayTimestamp(new Date(item.createdAt)),
      [StoragesTableField.CREATED_BY]: (
        item: ProjectStorageWithParentStorage,
      ) => item.createdBy,
    }),
    [t],
  );

  const customComparator: CustomComparatorConfig<
    ProjectStorageWithParentStorage,
    StoragesTableField
  > = {
    [SecretsTableField.NAME]: (a, b) =>
      a?.storage.name.localeCompare(b?.storage.name),
    [SecretsTableField.TYPE]: (a, b) =>
      a?.storage.type.localeCompare(b?.storage.type),
  };

  return (
    <div>
      <ClientSideDataTable
        data={filteredData}
        columns={columns}
        customComparator={customComparator}
        customRenderers={customRenderers}
        defaultSortByField={'name'}
        translation={t}
        idKey={'id'}
        isLoading={isSecretsLoading}
        rowActions={actions}
      />
    </div>
  );
};

export default ProjectStoragesTable;
