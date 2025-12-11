// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';
import { useTranslation } from 'next-i18next';

import { getFilteredData } from '@/utils/app/data-table';
import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { SecretsTableField } from '@/types/enums/secrets-table-field';
import { ClientSideDataFilter } from '@/types/filters';
import { ProjectSecretWithParentSecret } from '@/types/secrets';
import { SecretUseCase } from '@/types/enums/secrets';
import {
  ClientSideDataTable,
  StatusDisplay,
  DateDisplay,
} from '@/components/shared/DataTable';

import getProjectSecretStatusVariants from '@/utils/app/project-secret-status-variants';
import { ProjectSecretStatus } from '@/types/enums/secrets';
import StatusError from '@/components/shared/StatusError/StatusError';

interface Props {
  filters?: ClientSideDataFilter<ProjectSecretWithParentSecret>[];
  actions?: ActionItem<ProjectSecretWithParentSecret>[];
  isLoading: boolean;
  projectSecrets: ProjectSecretWithParentSecret[];
}

export const ProjectSecretsTable: React.FC<Props> = ({
  filters,
  actions,
  isLoading,
  projectSecrets,
}) => {
  const { t } = useTranslation('secrets');

  const filteredData = useMemo(() => {
    return getFilteredData(projectSecrets, filters);
  }, [projectSecrets, filters]);

  const columns: TableColumns<SecretsTableField | null> = [
    {
      key: SecretsTableField.NAME,
      sortable: true,
    },
    {
      key: SecretsTableField.STATUS,
      sortable: true,
    },
    {
      key: SecretsTableField.TYPE,
      sortable: true,
    },
    {
      key: SecretsTableField.USE_CASE,
      sortable: true,
    },
    {
      key: SecretsTableField.SCOPE,
      sortable: true,
    },
    {
      key: SecretsTableField.UPDATED_AT,
      sortable: true,
    },
  ];
  const customRenderers = useMemo(
    () => ({
      [SecretsTableField.NAME]: (item: ProjectSecretWithParentSecret) => (
        <span>{item.secret.name}</span>
      ),
      [SecretsTableField.STATUS]: (item: ProjectSecretWithParentSecret) => (
        <StatusDisplay
          type={item.status}
          variants={getProjectSecretStatusVariants(t)}
          bypassProps={
            item.status === ProjectSecretStatus.FAILED ||
            item.status === ProjectSecretStatus.DELETE_FAILED ||
            item.status === ProjectSecretStatus.SYNCED_ERROR
              ? {
                  isClickable: true,
                  helpContent: <StatusError statusReason={item.statusReason} />,
                }
              : undefined
          }
        />
      ),
      [SecretsTableField.TYPE]: (item: ProjectSecretWithParentSecret) => (
        <span data-testid={`secret-type-${item.secret.type}`}>
          {t(`secretType.${item.secret.type}`)}
        </span>
      ),
      [SecretsTableField.USE_CASE]: (item: ProjectSecretWithParentSecret) => (
        <span data-testid={`secret-use-case-${item.secret.useCase}`}>
          {t(`useCase.${item.secret.useCase ?? SecretUseCase.GENERIC}`)}
        </span>
      ),
      [SecretsTableField.SCOPE]: (item: ProjectSecretWithParentSecret) => (
        <span data-testid={`secret-scope-${item.secret.scope}`}>
          {t(`secretScope.${item.secret.scope}`)}
        </span>
      ),
      [SecretsTableField.UPDATED_AT]: (item: ProjectSecretWithParentSecret) => (
        <DateDisplay date={item[SecretsTableField.UPDATED_AT]} />
      ),
    }),
    [t],
  );

  const customComparator: CustomComparatorConfig<
    ProjectSecretWithParentSecret,
    SecretsTableField
  > = {
    [SecretsTableField.NAME]: (a, b) =>
      a?.secret.name.localeCompare(b?.secret.name),
    [SecretsTableField.TYPE]: (a, b) =>
      a?.secret.type.localeCompare(b?.secret.type),
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

export default ProjectSecretsTable;
