// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useDisclosure } from '@heroui/react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'next-i18next';
import { getServerSession } from 'next-auth';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { fetchStorages } from '@/services/app';
import { getProjects } from '@/services/server';
import { getSecrets } from '@/services/server';
import { getStorages } from '@/services/server';

import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@amdenterpriseai/utils/app';
import { doesStorageDataNeedToBeRefreshed } from '@amdenterpriseai/utils/app';
import { authOptions } from '@amdenterpriseai/utils/server';
import {
  doesSecretDataNeedToBeRefreshed,
  isSecretActioning,
} from '@amdenterpriseai/utils/app';

import {
  ActionFieldHintType,
  ClientSideDataFilter,
  FilterValueMap,
} from '@amdenterpriseai/types';
import { ProjectStatus } from '@amdenterpriseai/types';
import { ProjectSecretStatus, SecretScope } from '@amdenterpriseai/types';
import { Project } from '@amdenterpriseai/types';
import { Secret, SecretsResponse } from '@amdenterpriseai/types';
import { StoragesResponse } from '@amdenterpriseai/types';

import {
  AddSecret,
  AssignSecret,
  SecretsTable,
} from '@/components/features/secrets';
import DeleteSecretModal from '@/components/features/secrets/DeleteSecretModal';
import { ActionButton } from '@amdenterpriseai/components';
import { fetchSecrets } from '@/services/app';
import { SecretsFilter } from '@/components/features/secrets';

interface Props {
  projects: Project[];
  secrets: SecretsResponse;
  storages: StoragesResponse;
}

const SecretsPage: React.FC<Props> = ({ projects, secrets, storages }) => {
  const { t } = useTranslation('secrets');

  // Additional modals for Resource Manager
  const {
    isOpen: isAddSecretFormOpen,
    onOpenChange: onAddSecretFormOpenChange,
    onClose,
  } = useDisclosure();

  const {
    isOpen: isAssignSecretFormOpen,
    onOpenChange: onAssignSecretFormOpenChange,
  } = useDisclosure();

  const { isOpen: isDeleteSecretOpen, onOpenChange: onDeleteSecretOpenChange } =
    useDisclosure();

  const { data: storagesData } = useQuery<StoragesResponse>({
    queryKey: ['storages'],
    queryFn: () => fetchStorages(),
    initialData: storages,
    refetchInterval: (query) => {
      return !query.state.data ||
        doesStorageDataNeedToBeRefreshed(query.state.data.data)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });
  const [filters, setFilters] = useState<ClientSideDataFilter<Secret>[]>([]);

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<Secret>[] = [];

    if (
      filters?.search &&
      filters.search.length > 0 &&
      !(filters.search.length === 1 && filters.search[0] === '')
    ) {
      newFilters.push({
        field: 'name',
        values: filters.search,
      });
    }

    if (filters?.type && filters.type.length > 0) {
      newFilters.push({
        field: 'type',
        values: filters.type,
      });
    }
    if (filters?.scope && filters.scope.length > 0) {
      newFilters.push({
        field: 'scope',
        values: filters.scope,
      });
    }

    setFilters(newFilters);
  }, []);

  const {
    data: secretsData,
    isLoading: isSecretsLoading,
    refetch: refetchSecrets,
  } = useQuery<SecretsResponse>({
    queryKey: ['secrets'],
    queryFn: fetchSecrets,
    initialData: secrets,
    refetchInterval: (query) => {
      return !query.state.data ||
        doesSecretDataNeedToBeRefreshed(query.state.data?.data)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  // State management at page level
  const [targetSecret, setTargetSecret] = useState<Secret | null>(null);

  const checkSecretIsAttachedToStorage = useCallback(
    (s: Secret) => {
      return storagesData?.data.some((storage) => storage.secretId === s.id);
    },
    [storagesData],
  );

  const checkSecretIsOrganizationScoped = useCallback((s: Secret) => {
    return s.scope !== SecretScope.ORGANIZATION;
  }, []);

  const checkDeleteDisabled = useCallback(
    (s: Secret) => {
      return checkSecretIsAttachedToStorage(s);
    },
    [checkSecretIsAttachedToStorage],
  );

  const checkAssignDisabled = useCallback(
    (s: Secret) => {
      return isSecretActioning(s) || checkSecretIsOrganizationScoped(s);
    },
    [checkSecretIsOrganizationScoped],
  );

  // Define all table actions
  const actions = useMemo(
    () => [
      {
        key: 'assign',
        onPress: (s: Secret) => {
          setTargetSecret(s);
          onAssignSecretFormOpenChange();
        },
        isDisabled: checkAssignDisabled,
        label: t('list.actions.assign.label'),
        hint: [
          {
            showHint: checkSecretIsOrganizationScoped,
            message: t('list.actions.assign.hint.scope'),
            type: ActionFieldHintType.WARNING,
          },
        ],
      },
      {
        key: 'delete',
        className: 'text-danger',
        color: 'danger',
        isDisabled: checkDeleteDisabled,
        onPress: (s: Secret) => {
          setTargetSecret(s);
          onDeleteSecretOpenChange();
        },
        label: t('list.actions.delete.label'),
        hint: [
          {
            showHint: checkSecretIsAttachedToStorage,
            message: t('list.actions.delete.hint.storage'),
            type: ActionFieldHintType.WARNING,
          },
        ],
      },
    ],
    [
      checkSecretIsAttachedToStorage,
      checkSecretIsOrganizationScoped,
      checkDeleteDisabled,
      checkAssignDisabled,
      onAssignSecretFormOpenChange,
      onDeleteSecretOpenChange,
      t,
    ],
  );

  const projectsNotReadyIds = useMemo(
    () =>
      projects
        .filter((project) => project.status !== ProjectStatus.READY)
        .map((project) => project.id) ?? [],
    [projects],
  );

  const projectSecretsActioningIds = useMemo(
    () =>
      targetSecret?.projectSecrets
        .filter(
          (ps) =>
            ps.status === ProjectSecretStatus.DELETING ||
            ps.status === ProjectSecretStatus.PENDING,
        )
        .map((ps) => ps.project.id) ?? [],
    [targetSecret],
  );

  return (
    <>
      <SecretsFilter
        onFilterChange={handleFilterChange}
        onRefresh={refetchSecrets}
        actionButton={
          <ActionButton primary onPress={onAddSecretFormOpenChange}>
            {t('actions.add')}
          </ActionButton>
        }
      />

      <SecretsTable
        secrets={secretsData.data}
        isSecretsLoading={isSecretsLoading}
        filters={filters}
        actions={actions}
      />

      <AddSecret
        isOpen={isAddSecretFormOpen}
        onClose={onClose}
        onCreateSuccess={refetchSecrets}
        secrets={secretsData.data}
        projects={projects}
        disabledProjectIds={projectsNotReadyIds}
        defaultScope={SecretScope.ORGANIZATION}
        scopeSelectDisabled={false}
        projectSelectDisabled={false}
      />
      <AssignSecret
        isOpen={isAssignSecretFormOpen}
        onClose={onAssignSecretFormOpenChange}
        projects={projects}
        secret={targetSecret}
        selectedProjectIds={
          targetSecret?.projectSecrets.map((ps) => ps.project.id) ?? []
        }
        disabledProjectIds={projectSecretsActioningIds.concat(
          projectsNotReadyIds,
        )}
      />
      <DeleteSecretModal
        isOpen={isDeleteSecretOpen}
        onOpenChange={onDeleteSecretOpenChange}
        secret={targetSecret}
        queryKeyToInvalidate={['secrets']}
      />
    </>
  );
};

export default SecretsPage;

export async function getServerSideProps(context: any) {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  const secrets = await getSecrets(session?.accessToken as string);
  const projects = await getProjects(session?.accessToken as string);
  const storages = await getStorages(session?.accessToken as string);

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'common',
        'secrets',
        'sharedComponents',
      ])),
      projects: projects?.data || [],
      secrets,
      storages,
    },
  };
}
