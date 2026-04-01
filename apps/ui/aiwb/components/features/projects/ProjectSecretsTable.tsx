// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';
import { useTranslation } from 'next-i18next';

import { getFilteredData } from '@amdenterpriseai/utils/app';
import { ActionItem, TableColumns } from '@amdenterpriseai/types';
import { CustomComparatorConfig } from '@amdenterpriseai/types';
import { SecretsTableField } from '@amdenterpriseai/types';
import { ClientSideDataFilter } from '@amdenterpriseai/types';
import { ProjectSecretWithParentSecret } from '@amdenterpriseai/types';
import { SecretUseCase } from '@amdenterpriseai/types';
import {
  ClientSideDataTable,
  StatusDisplay,
  DateDisplay,
} from '@amdenterpriseai/components';

import { getProjectSecretStatusVariants } from '@amdenterpriseai/utils/app';
import { ProjectSecretStatus } from '@amdenterpriseai/types';
import { StatusError } from '@amdenterpriseai/components';

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
          additionalProps={
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
