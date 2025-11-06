// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React, { useCallback, useMemo, useState } from 'react';
import { useDisclosure } from '@heroui/react';
import { useTranslation } from 'next-i18next';
import { useQuery } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';

import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';
import DeleteSecretModal from './DeleteSecretModal';
import { SecretsTable } from './SecretsTable';

import { fetchWorkbenchSecrets } from '@/services/app/secrets';
import {
  doesSecretDataNeedToBeRefreshed,
  isSecretActioning,
} from '@/utils/app/secrets';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';
import { useSecretsFilters } from '@/hooks/useSecretsFilters';
import { useProject } from '@/contexts/ProjectContext';
import { SecretsResponse, Secret } from '@/types/secrets';
import { SecretStatus } from '@/types/enums/secrets';

interface Props {
  initialSecrets: SecretsResponse;
}

export const WorkbenchSecretsPageContent: React.FC<Props> = ({
  initialSecrets,
}) => {
  const { t } = useTranslation('secrets');

  // State management at component level
  const [targetSecret, setTargetSecret] = useState<Secret | null>(null);

  // Get active project from context
  const { activeProject } = useProject();

  // Session for RBAC
  const { data: session } = useSession();

  // React Query for fetching workbench secrets - refetch when project changes
  const { data: secretsData, isLoading: isSecretsLoading } =
    useQuery<SecretsResponse>({
      queryKey: ['project', activeProject, 'workbench-secrets'],
      queryFn: () => fetchWorkbenchSecrets(activeProject!),
      initialData: initialSecrets,
      refetchInterval: (query) => {
        return !query.state.data ||
          doesSecretDataNeedToBeRefreshed(query.state.data?.secrets)
          ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
          : false;
      },
      enabled: !!session?.user, // Fetch for all authenticated users
    });

  const { filters, handleFilterChange, filterConfig } = useSecretsFilters({
    includeScope: false, // Workbench doesn't show scope column
  });

  // Disclosure for delete modal
  const { isOpen: isDeleteSecretOpen, onOpenChange: onDeleteSecretOpenChange } =
    useDisclosure();

  // Check if user can delete secrets
  const canDeleteSecrets = useCallback(
    (secret: Secret) => {
      // Basic auth check
      if (!session?.user || !activeProject) return false;

      // Check if secret is in a deleteable state
      if (secret.status === SecretStatus.DELETING) return false;

      // Check if the secret is assigned to the current project
      const projectAssignment = secret.projectSecrets?.find(
        (ps) => ps.projectId === activeProject,
      );

      // Any member of the project can delete secrets assigned to their project
      return !!projectAssignment;
    },
    [session, activeProject],
  );

  // Actions for secrets table
  const actions = useMemo(() => {
    const baseActions = [];

    // Add delete action with per-secret permission check
    baseActions.push({
      key: 'delete',
      className: 'text-danger',
      color: 'danger',
      isDisabled: (s: Secret) => isSecretActioning(s) || !canDeleteSecrets(s),
      onPress: (s: Secret) => {
        setTargetSecret(s);
        onDeleteSecretOpenChange();
      },
      label: t('list.actions.delete.label'),
    });

    return baseActions;
  }, [t, onDeleteSecretOpenChange, canDeleteSecrets]);

  return (
    <div className="py-8">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
      />

      <SecretsTable
        secrets={secretsData?.secrets || []}
        isSecretsLoading={isSecretsLoading}
        filters={filters}
        actions={actions}
        showScopeColumn={false}
        showAssignedToColumn={false}
      />

      <DeleteSecretModal
        isOpen={isDeleteSecretOpen}
        onOpenChange={onDeleteSecretOpenChange}
        secret={targetSecret}
        projectId={activeProject!}
        queryKeyToInvalidate={['project', activeProject!, 'workbench-secrets']}
      />
    </div>
  );
};

export default WorkbenchSecretsPageContent;
