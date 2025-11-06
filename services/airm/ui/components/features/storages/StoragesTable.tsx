// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Chip, Tooltip } from '@heroui/react';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { StoragesTableField } from '@/types/enums/storages';
import { ProjectStorage, Storage } from '@/types/storages';

import { ClientSideDataTable } from '@/components/shared/DataTable';
import {
  DateDisplay,
  NoDataDisplay,
} from '@/components/shared/DataTable/CustomRenderers';

import { StorageStatus } from './StorageStatus';

interface Props {
  actions?: ActionItem<Storage>[];
  storages: Storage[];
  isStoragesLoading: boolean;
}

export const StoragesTable: React.FC<Props> = ({
  actions,
  storages,
  isStoragesLoading,
}) => {
  const { t } = useTranslation('storages');

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
      key: StoragesTableField.SCOPE,
      sortable: true,
    },

    {
      key: StoragesTableField.ASSIGNED_TO,
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
      [StoragesTableField.NAME]: (item: Storage) => {
        return <span>{item.name}</span>;
      },
      [StoragesTableField.TYPE]: (item: Storage) => {
        return <Chip>{t(`storageType.${item.type}`)}</Chip>;
      },
      [StoragesTableField.STATUS]: (item: Storage) => {
        const secondaryStatusReasons = item.projectStorages
          .filter((s) => s.statusReason !== null)
          .map((s) => ({
            key: s.projectName,
            description: s.statusReason ?? '',
          }));

        return (
          <StorageStatus
            status={item.status}
            statusReason={item.statusReason}
            secondaryStatusReason={
              secondaryStatusReasons.length > 0
                ? secondaryStatusReasons
                : undefined
            }
          />
        );
      },
      [StoragesTableField.SCOPE]: (item: Storage) => {
        return t(`storageScope.${item.scope}`); // TODO: Update to use item.scope when avaliable
      },
      [StoragesTableField.ASSIGNED_TO]: (item: Storage) => {
        return item.projectStorages && item.projectStorages.length === 1 ? (
          <span>{item.projectStorages[0].projectName}</span>
        ) : item.projectStorages && item.projectStorages.length > 1 ? (
          <Tooltip
            content={
              <ul className="p-2 list-disc list-inside">
                {item.projectStorages.map((projectStorage: ProjectStorage) => (
                  <li key={projectStorage.id}>{projectStorage.projectName}</li>
                ))}
              </ul>
            }
            placement="top"
          >
            <span className="cursor-pointer underline">{`${item.projectStorages.length} projects`}</span>
          </Tooltip>
        ) : (
          <NoDataDisplay />
        );
      },
      [StoragesTableField.CREATED_AT]: (item: Storage) => (
        <DateDisplay date={item[StoragesTableField.CREATED_AT]} />
      ),
      [StoragesTableField.CREATED_BY]: (item: Storage) => {
        return <span>{item.createdBy}</span>;
      },
    }),
    [t],
  );

  return (
    <div>
      <ClientSideDataTable
        data={storages}
        columns={columns}
        customRenderers={customRenderers}
        defaultSortByField={'name'}
        translation={t}
        idKey={'id'}
        isLoading={isStoragesLoading}
        rowActions={actions}
      />
    </div>
  );
};

export default StoragesTable;
