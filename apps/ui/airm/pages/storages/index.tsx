// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useDisclosure } from '@heroui/react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { fetchProjects } from '@/services/app';
import { fetchSecrets } from '@/services/app';
import { fetchStorages } from '@/services/app';
import { getProjects } from '@/services/server';
import { getSecrets } from '@/services/server';
import { getStorages } from '@/services/server';

import {
  DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA,
  doesProjectDataNeedToBeRefreshed,
} from '@amdenterpriseai/utils/app';
import { getFilteredData } from '@amdenterpriseai/utils/app';
import { doesSecretDataNeedToBeRefreshed } from '@amdenterpriseai/utils/app';
import { doesStorageDataNeedToBeRefreshed } from '@amdenterpriseai/utils/app';
import { authOptions } from '@amdenterpriseai/utils/server';

import { ProjectStatus, SecretScope } from '@amdenterpriseai/types';
import { SecretUseCase } from '@amdenterpriseai/types';
import {
  ProjectStorageStatus,
  StorageStatus,
  StorageType,
} from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import {
  ProjectWithResourceAllocation,
  ProjectsResponse,
} from '@amdenterpriseai/types';
import { Secret, SecretsResponse } from '@amdenterpriseai/types';
import { Storage, StoragesResponse } from '@amdenterpriseai/types';

import { AddSecret } from '@/components/features/secrets';
import {
  AddS3Storage,
  AssignStorage,
  DeleteStorageModal,
  StoragesTable,
} from '@/components/features/storages';
import { StoragesFilter } from '@/components/features/storages';
import AddStorageButton from '@/components/features/storages/AddStorageButton';

interface Props {
  projects: ProjectWithResourceAllocation[];
  secrets: Secret[];
  storages: Storage[];
}

const StoragesPage: React.FC<Props> = ({ projects, secrets, storages }) => {
  const { t } = useTranslation('storages');
  const {
    isOpen: isAddStorageFormOpen,
    onOpenChange: onAddStorageFormOpenChange,
    onClose: onAddStorageFormClose,
  } = useDisclosure();

  const {
    isOpen: isAddSecretFormOpen,
    onOpenChange: onAddSecretFormOpenChange,
    onClose: onAddSecretFormClose,
  } = useDisclosure();

  const {
    data: storagesData,
    isLoading: isStoragesLoading,
    refetch: refetchStorages,
  } = useQuery<StoragesResponse>({
    queryKey: ['storages'],
    queryFn: () => fetchStorages(),
    initialData: {
      data: storages,
    },
    refetchInterval: (query) => {
      return !query.state.data ||
        doesStorageDataNeedToBeRefreshed(query.state.data.data)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  const { data: secretsData, refetch: refetchSecrets } =
    useQuery<SecretsResponse>({
      queryKey: ['secrets'],
      queryFn: () => fetchSecrets(),
      initialData: {
        data: secrets,
      },
      refetchInterval: (query) => {
        return !query.state.data ||
          doesSecretDataNeedToBeRefreshed(query.state.data.data)
          ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
          : false;
      },
    });

  const { data: projectsData } = useQuery<ProjectsResponse>({
    queryKey: ['projects'],
    queryFn: () => fetchProjects(),
    initialData: {
      data: projects,
    },
    refetchInterval: (query) => {
      return !query.state.data ||
        doesProjectDataNeedToBeRefreshed(query.state.data.data)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  const [filters, setFilters] = useState<ClientSideDataFilter<Storage>[]>([]);

  const [targetStorage, setTargetStorage] = useState<Storage | null>(null);

  const filteredData = useMemo(() => {
    const storagesList = storagesData?.data || [];
    return getFilteredData(storagesList, filters);
  }, [storagesData, filters]);

  const {
    isOpen: isAssignStorageFormOpen,
    onOpenChange: onAssignStorageFormOpenChange,
  } = useDisclosure();

  const {
    isOpen: isDeleteStorageOpen,
    onOpenChange: onDeleteStorageOpenChange,
  } = useDisclosure();

  const checkStorageActioning = (s: Storage) => {
    return (
      s.status === StorageStatus.DELETING || s.status === StorageStatus.PENDING
    );
  };

  const actions = useMemo(() => {
    return [
      {
        key: 'edit',
        onPress: (s: Storage) => {
          setTargetStorage(s);
          onAssignStorageFormOpenChange();
        },
        isDisabled: checkStorageActioning,
        label: t('list.actions.assign.label'),
      },
      {
        key: 'delete',
        className: 'text-danger',
        color: 'danger',
        isDisabled: checkStorageActioning,
        onPress: (s: Storage) => {
          setTargetStorage(s);
          onDeleteStorageOpenChange();
        },
        label: t('list.actions.delete.label'),
      },
    ];
  }, [t, onAssignStorageFormOpenChange, onDeleteStorageOpenChange]);

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<Storage>[] = [];
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
    setFilters(newFilters);
  }, []);

  const projectsNotReadyIds = useMemo(
    () =>
      projects
        .filter((project) => project.status !== ProjectStatus.READY)
        .map((project) => project.id) ?? [],
    [projects],
  );

  const projectStoragesActioningIds = useMemo(
    () =>
      targetStorage?.projectStorages
        .filter(
          (ps) =>
            ps.status === ProjectStorageStatus.DELETING ||
            ps.status === ProjectStorageStatus.PENDING,
        )
        .map((ps) => ps.project.id) ?? [],
    [targetStorage],
  );

  return (
    <>
      <div className="flex items-center justify-between pb-4">
        <StoragesFilter
          onFilterChange={handleFilterChange}
          onRefresh={refetchStorages}
          actionButton={
            <AddStorageButton
              storageTypes={{
                [StorageType.S3]: onAddStorageFormOpenChange,
              }}
            />
          }
        />
      </div>

      <AddS3Storage
        isOpen={isAddStorageFormOpen}
        secrets={secretsData?.data || secrets}
        projects={projectsData?.data || projects}
        storages={storagesData?.data || storages}
        disabledProjectIds={projectsNotReadyIds}
        onClose={onAddStorageFormClose}
        openAddSecret={onAddSecretFormOpenChange}
      />

      <AddSecret
        isOpen={isAddSecretFormOpen}
        secrets={secretsData?.data || secrets}
        projects={projectsData?.data || projects}
        onClose={onAddSecretFormClose}
        restrictToUseCases={[SecretUseCase.S3]}
        onCreateSuccess={refetchSecrets}
        defaultScope={SecretScope.ORGANIZATION}
        scopeSelectDisabled={true}
        projectSelectDisabled={false}
      />

      {targetStorage ? (
        <AssignStorage
          isOpen={isAssignStorageFormOpen}
          storage={targetStorage}
          onClose={onAssignStorageFormOpenChange}
          projects={projectsData?.data || projects}
          selectedProjectIds={
            targetStorage?.projectStorages.map((ps) => ps.project.id) ?? []
          }
          disabledProjectIds={projectStoragesActioningIds.concat(
            projectsNotReadyIds,
          )}
        />
      ) : null}

      {targetStorage ? (
        <DeleteStorageModal
          isOpen={isDeleteStorageOpen}
          storage={targetStorage}
          onOpenChange={onDeleteStorageOpenChange}
        />
      ) : null}

      <StoragesTable
        storages={filteredData}
        isStoragesLoading={isStoragesLoading}
        actions={actions}
      />
    </>
  );
};

export default StoragesPage;

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

  const projects = await getProjects(session?.accessToken as string);
  const secrets = await getSecrets(session?.accessToken as string);
  const storages = await getStorages(session?.accessToken as string);

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'common',
        'storages',
        'secrets',
        'sharedComponents',
      ])),
      projects: projects?.data || [],
      secrets: secrets?.data || [],
      storages: storages?.data || [],
    },
  };
}
