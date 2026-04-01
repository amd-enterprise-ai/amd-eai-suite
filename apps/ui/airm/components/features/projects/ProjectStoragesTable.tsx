// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Chip } from '@heroui/react';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';
import { useAccessControl } from '@/hooks/useAccessControl';
import { getFilteredData } from '@amdenterpriseai/utils/app';
import { displayTimestamp } from '@amdenterpriseai/utils/app';

import { ActionItem, TableColumns } from '@amdenterpriseai/types';
import { CustomComparatorConfig } from '@amdenterpriseai/types';
import { SecretsTableField } from '@amdenterpriseai/types';
import { StoragesTableField } from '@amdenterpriseai/types';
import { ClientSideDataFilter } from '@amdenterpriseai/types';
import { ProjectStorageWithParentStorage } from '@amdenterpriseai/types';

import {
  ClientSideDataTable,
  StatusDisplay,
} from '@amdenterpriseai/components';
import { getProjectStorageStatusVariants } from '@amdenterpriseai/utils/app';
import { StatusError } from '@amdenterpriseai/components';
// import { ProjectStorageStatus } from "../storages";
import { ProjectStorageStatus } from '@amdenterpriseai/types';

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
  const { isAdministrator } = useAccessControl();

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
          additionalProps={
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
        return t(`storageScope.${item.scope}`);
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
        rowActions={isAdministrator ? actions : undefined}
      />
    </div>
  );
};

export default ProjectStoragesTable;
