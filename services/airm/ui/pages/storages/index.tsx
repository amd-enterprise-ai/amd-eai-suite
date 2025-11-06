// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useDisclosure } from '@heroui/react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { fetchProjects } from '@/services/app/projects';
import { fetchSecrets } from '@/services/app/secrets';
import { fetchStorages } from '@/services/app/storages';
import { getProjects } from '@/services/server/projects';
import { getSecrets } from '@/services/server/secrets';
import { getStorages } from '@/services/server/storages';

import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';
import { getFilteredData } from '@/utils/app/data-table';
import { doesDataNeedToBeRefreshed } from '@/utils/app/projects';
import { doesSecretDataNeedToBeRefreshed } from '@/utils/app/secrets';
import { doesStorageDataNeedToBeRefreshed } from '@/utils/app/storages';
import { authOptions } from '@/utils/server/auth';

import { ProjectStatus } from '@/types/enums/projects';
import {
  ProjectStorageStatus,
  StorageStatus,
  StorageType,
} from '@/types/enums/storages';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import {
  ProjectWithResourceAllocation,
  ProjectsResponse,
} from '@/types/projects';
import { Secret, SecretsResponse } from '@/types/secrets';
import { Storage, StoragesResponse } from '@/types/storages';

import { AddSecret } from '@/components/features/secrets';
import {
  AddS3Storage,
  AssignStorage,
  DeleteStorageModal,
  StoragesTable,
} from '@/components/features/storages';
import { StoragesListFilter } from '@/components/features/storages';
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

  const { data: storagesData, isLoading: isStoragesLoading } =
    useQuery<StoragesResponse>({
      queryKey: ['storages'],
      queryFn: () => fetchStorages(),
      initialData: {
        storages,
      },
      refetchInterval: (query) => {
        return !query.state.data ||
          doesStorageDataNeedToBeRefreshed(query.state.data.storages)
          ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
          : false;
      },
    });

  const { data: secretsData } = useQuery<SecretsResponse>({
    queryKey: ['secrets'],
    queryFn: () => fetchSecrets(),
    initialData: {
      secrets,
    },
    refetchInterval: (query) => {
      return !query.state.data ||
        doesSecretDataNeedToBeRefreshed(query.state.data.secrets)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  const { data: projectsData } = useQuery<ProjectsResponse>({
    queryKey: ['projects'],
    queryFn: () => fetchProjects(),
    initialData: {
      projects: projects,
    },
    refetchInterval: (query) => {
      return !query.state.data ||
        doesDataNeedToBeRefreshed(query.state.data.projects)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  const [filters, setFilters] = useState<ClientSideDataFilter<Storage>[]>([]);

  const [targetStorage, setTargetStorage] = useState<Storage | null>(null);

  const filteredData = useMemo(() => {
    const data = storagesData?.storages || [];
    return getFilteredData(data, filters);
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
      filters &&
      filters.search &&
      filters.search.length > 0 &&
      !(filters.search.length === 1 && filters.search[0] === '')
    ) {
      newFilters.push({
        field: 'name',
        values: filters.search,
      });
    }
    if (filters && filters.scope && filters.scope.length > 0) {
      newFilters.push({
        field: 'scope',
        values: filters.scope,
      });
    }
    if (filters && filters.type && filters.type.length > 0) {
      newFilters.push({
        field: 'type',
        values: filters.type,
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
        .map((ps) => ps.projectId) ?? [],
    [targetStorage],
  );

  return (
    <div className="py-8">
      <div className="flex items-center justify-between pb-4">
        <StoragesListFilter
          onFilterChange={handleFilterChange}
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
        secrets={secretsData?.secrets || secrets}
        projects={projectsData?.projects || projects}
        storages={storagesData?.storages || storages}
        disabledProjectIds={projectsNotReadyIds}
        onClose={onAddStorageFormClose}
        openAddSecret={onAddSecretFormOpenChange}
      />

      <AddSecret
        isOpen={isAddSecretFormOpen}
        secrets={secretsData?.secrets || secrets}
        projects={projectsData?.projects || projects}
        onClose={onAddSecretFormClose}
      />

      {targetStorage ? (
        <AssignStorage
          isOpen={isAssignStorageFormOpen}
          storage={targetStorage}
          onClose={onAssignStorageFormOpenChange}
          projects={projectsData?.projects || projects}
          selectedProjectIds={
            targetStorage?.projectStorages.map((ps) => ps.projectId) ?? []
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
    </div>
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
      ])),
      projects: projects?.projects || [],
      secrets: secrets?.secrets || [],
      storages: storages?.storages || [],
    },
  };
}
