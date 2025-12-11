// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Chip } from '@heroui/react';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { getFilteredData } from '@/utils/app/data-table';
import { displayTimestamp } from '@/utils/app/strings';

import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { SecretsTableField } from '@/types/enums/secrets-table-field';
import { StoragesTableField } from '@/types/enums/storages';
import { ClientSideDataFilter } from '@/types/filters';
import { ProjectStorageWithParentStorage } from '@/types/storages';

import {
  ClientSideDataTable,
  StatusDisplay,
} from '@/components/shared/DataTable';
import getProjectStorageStatusVariants from '@/utils/app/project-storage-status-variants';
import StatusError from '@/components/shared/StatusError/StatusError';
// import { ProjectStorageStatus } from "../storages";
import { ProjectStorageStatus } from '@/types/enums/storages';

interface Props {
  filters?: ClientSideDataFilter<ProjectStorageWithParentStorage>[];
  actions?: ActionItem<ProjectStorageWithParentStorage>[];
  projectStorages: ProjectStorageWithParentStorage[];
  isLoading: boolean;
}

export const ProjectStoragesTable: React.FC<Props> = ({
  filters,
  actions,
  isLoading,
  projectStorages,
}) => {
  const { t } = useTranslation('storages');

  const filteredData = useMemo(() => {
    return getFilteredData(projectStorages, filters);
  }, [projectStorages, filters]);

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
        <StatusDisplay
          type={item.status}
          variants={getProjectStorageStatusVariants(t)}
          bypassProps={
            (item.status === ProjectStorageStatus.FAILED ||
              item.status === ProjectStorageStatus.DELETE_FAILED ||
              item.status === ProjectStorageStatus.SYNCED_ERROR) &&
            !!item.statusReason
              ? {
                  isClickable: true,
                  helpContent: <StatusError statusReason={item.statusReason} />,
                }
              : undefined
          }
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
        isLoading={isLoading}
        rowActions={actions}
      />
    </div>
  );
};

export default ProjectStoragesTable;
