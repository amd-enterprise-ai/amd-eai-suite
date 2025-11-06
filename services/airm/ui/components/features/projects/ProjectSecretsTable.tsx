// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { fetchProjectSecrets } from '@/services/app/secrets';

import { getFilteredData } from '@/utils/app/data-table';
import { displayTimestamp } from '@/utils/app/strings';

import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { SecretsTableField } from '@/types/enums/secrets-table-field';
import { ClientSideDataFilter } from '@/types/filters';
import {
  ProjectSecretWithParentSecret,
  ProjectSecretsResponse,
} from '@/types/secrets';

import { ClientSideDataTable } from '@/components/shared/DataTable';

import { ProjectSecretStatus } from '../secrets';
import { doesProjectSecretDataNeedToBeRefreshed } from '@/utils/app/secrets';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';

interface Props {
  filters?: ClientSideDataFilter<ProjectSecretWithParentSecret>[];
  actions?: ActionItem<ProjectSecretWithParentSecret>[];
  projectId: string;
  projectSecrets: ProjectSecretWithParentSecret[];
}

export const ProjectSecretsTable: React.FC<Props> = ({
  filters,
  actions,
  projectId,
  projectSecrets,
}) => {
  const { t } = useTranslation('secrets');

  const { data: projectSecretsData, isLoading: isSecretsLoading } =
    useQuery<ProjectSecretsResponse>({
      queryKey: ['secrets', projectId],
      queryFn: () => fetchProjectSecrets(projectId),
      initialData: {
        projectSecrets: projectSecrets,
      },
      refetchInterval: (query) => {
        return !query.state.data ||
          doesProjectSecretDataNeedToBeRefreshed(
            query.state.data.projectSecrets,
          )
          ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
          : false;
      },
    });

  const filteredData = useMemo(() => {
    const data = projectSecretsData.projectSecrets;
    return getFilteredData(data, filters);
  }, [projectSecretsData, filters]);

  const columns: TableColumns<SecretsTableField | null> = [
    {
      key: SecretsTableField.NAME,
      sortable: true,
    },
    {
      key: SecretsTableField.TYPE,
      sortable: true,
    },
    {
      key: SecretsTableField.STATUS,
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
      [SecretsTableField.TYPE]: (item: ProjectSecretWithParentSecret) => (
        <span data-testid={`secret-type-${item.secret.type}`}>
          {t(`secretType.${item.secret.type}`)}
        </span>
      ),
      [SecretsTableField.STATUS]: (item: ProjectSecretWithParentSecret) => (
        <ProjectSecretStatus
          status={item.status}
          statusReason={item.statusReason}
        />
      ),
      [SecretsTableField.UPDATED_AT]: (item: ProjectSecretWithParentSecret) =>
        displayTimestamp(new Date(item.updatedAt)),
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
        isLoading={isSecretsLoading}
        rowActions={actions}
      />
    </div>
  );
};

export default ProjectSecretsTable;
