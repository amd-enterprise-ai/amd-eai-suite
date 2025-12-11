// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tooltip } from '@heroui/react';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { getFilteredData } from '@/utils/app/data-table';

import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { SecretsTableField } from '@/types/enums/secrets-table-field';
import { ClientSideDataFilter } from '@/types/filters';
import { Secret } from '@/types/secrets';

import { SecretStatus } from '@/types/enums/secrets';

import { ClientSideDataTable } from '@/components/shared/DataTable';
import {
  StatusDisplay,
  DateDisplay,
  NoDataDisplay,
} from '@/components/shared/DataTable/CustomRenderers';

import { StatusError } from '@/components/shared/StatusError';
import SecretProjectAssignedTo from './SecretProjectAssignedTo';
import getSecretStatusVariants from '@/utils/app/secrets-status-variants';

interface Props {
  filters?: ClientSideDataFilter<Secret>[];
  actions?: ActionItem<Secret>[];
  secrets: Secret[];
  isSecretsLoading: boolean;
  showScopeColumn?: boolean;
  showAssignedToColumn?: boolean;
}

export const SecretsTable: React.FC<Props> = ({
  filters,
  actions,
  secrets,
  isSecretsLoading,
  showScopeColumn = true,
  showAssignedToColumn = true,
}) => {
  const { t } = useTranslation('secrets');

  const filteredData = useMemo(() => {
    const data = secrets;
    return getFilteredData(data, filters);
  }, [secrets, filters]);

  const columns: TableColumns<SecretsTableField | null> = useMemo(() => {
    const columns = [
      {
        key: SecretsTableField.NAME,
        sortable: true,
      },
      {
        key: SecretsTableField.TYPE,
        sortable: true,
      },
      {
        key: SecretsTableField.USE_CASE,
        sortable: false,
      },
      {
        key: SecretsTableField.STATUS,
        sortable: true,
      },
    ];

    // Conditionally add scope column
    if (showScopeColumn) {
      columns.push({
        key: SecretsTableField.SCOPE,
        sortable: true,
      });
    }

    // Conditionally add assigned to column
    if (showAssignedToColumn) {
      columns.push({
        key: SecretsTableField.ASSIGNED_TO,
        sortable: false,
      });
    }

    // Always add updated at column at the end
    columns.push({
      key: SecretsTableField.UPDATED_AT,
      sortable: true,
    });

    return columns;
  }, [showScopeColumn, showAssignedToColumn]);
  const customRenderers = useMemo(
    () => ({
      [SecretsTableField.NAME]: (item: Secret) => {
        return (
          <Tooltip content={item.name} placement="top">
            <div className={'max-w-64 truncate'}>{item.name}</div>
          </Tooltip>
        );
      },
      [SecretsTableField.TYPE]: (item: Secret) => {
        return (
          <span data-testid={`secret-type-${item.type}`}>
            {t(`secretType.${item.type}`)}
          </span>
        );
      },
      [SecretsTableField.STATUS]: (item: Secret) => {
        const { status, statusReason } = item;
        const secondaryStatusReasons = item.projectSecrets
          .filter((s) => s.statusReason !== null)
          .map((s) => ({
            key: s.projectName,
            description: s.statusReason ?? '',
          }));

        const hasError =
          (status === SecretStatus.FAILED ||
            status === SecretStatus.DELETE_FAILED ||
            status === SecretStatus.SYNCED_ERROR) &&
          (!!statusReason || secondaryStatusReasons.length > 0);

        return (
          <>
            {status === SecretStatus.UNASSIGNED ? (
              <NoDataDisplay />
            ) : (
              <StatusDisplay
                type={status}
                variants={getSecretStatusVariants(t)}
                bypassProps={
                  hasError
                    ? {
                        isClickable: true,
                        helpContent: (
                          <StatusError
                            statusReason={statusReason}
                            secondaryStatusReasons={secondaryStatusReasons}
                          />
                        ),
                      }
                    : undefined
                }
              />
            )}

            {/* <SecretStatus
              status={item.status}
              statusReason={item.statusReason}
              secondaryStatusReason={
                secondaryStatusReasons.length > 0
                  ? secondaryStatusReasons
                  : undefined
              }
            /> */}
          </>
        );
      },
      [SecretsTableField.SCOPE]: (item: Secret) => {
        return t(`secretScope.${item.scope}`); // TODO: Update to use item.scope when avaliable
      },
      [SecretsTableField.USE_CASE]: (item: Secret) => {
        return item.useCase ? (
          <span>{t(`useCase.${item.useCase}`)}</span>
        ) : (
          <NoDataDisplay />
        );
      },
      [SecretsTableField.ASSIGNED_TO]: (item: Secret) => {
        return <SecretProjectAssignedTo secret={item} />;
      },
      [SecretsTableField.UPDATED_AT]: (item: Secret) => (
        <DateDisplay date={item[SecretsTableField.UPDATED_AT]} />
      ),
    }),
    [t],
  );

  return (
    <div>
      <ClientSideDataTable
        data={filteredData}
        columns={columns}
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

export default SecretsTable;
