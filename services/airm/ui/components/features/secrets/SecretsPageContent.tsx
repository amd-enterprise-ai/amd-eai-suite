// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { useQuery } from '@tanstack/react-query';

import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';
import { SecretsTable } from './SecretsTable';

import { useSecretsFilters } from '@/hooks/useSecretsFilters';
import { fetchSecrets } from '@/services/app/secrets';
import { doesSecretDataNeedToBeRefreshed } from '@/utils/app/secrets';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';
import { SecretsResponse } from '@/types/secrets';

interface Props {
  initialSecrets: SecretsResponse;
  showScopeColumn?: boolean;
  showAssignedToColumn?: boolean;
  showAddButton?: boolean;
  additionalActions?: React.ReactNode;
  additionalModals?: React.ReactNode;
  actions: any[];
}

/**
 * Secrets page content component for Resource Manager.
 * Provides configurable column visibility, custom actions, and modals.
 * All actions are defined by parent component.
 */
export const SecretsPageContent: React.FC<Props> = ({
  initialSecrets,
  showScopeColumn = true,
  showAssignedToColumn = true,
  showAddButton = false,
  additionalActions,
  additionalModals,
  actions,
}) => {
  // Hooks
  const { filters, handleFilterChange, filterConfig } = useSecretsFilters({
    includeScope: showScopeColumn,
  });

  // React Query for fetching secrets
  const { data: secretsData, isLoading: isSecretsLoading } =
    useQuery<SecretsResponse>({
      queryKey: ['secrets'],
      queryFn: fetchSecrets,
      initialData: initialSecrets,
      refetchInterval: (query) => {
        return !query.state.data ||
          doesSecretDataNeedToBeRefreshed(query.state.data?.secrets)
          ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
          : false;
      },
    });

  return (
    <div className="py-8">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        endContent={showAddButton ? additionalActions : undefined}
      />

      <SecretsTable
        secrets={secretsData.secrets}
        isSecretsLoading={isSecretsLoading}
        filters={filters}
        actions={actions}
        showScopeColumn={showScopeColumn}
        showAssignedToColumn={showAssignedToColumn}
      />

      {additionalModals}
    </div>
  );
};

export default SecretsPageContent;
