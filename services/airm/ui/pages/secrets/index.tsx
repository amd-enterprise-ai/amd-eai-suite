// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useDisclosure } from '@heroui/react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'next-i18next';
import { getServerSession } from 'next-auth';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { fetchStorages } from '@/services/app/storages';
import { getProjects } from '@/services/server/projects';
import { getSecrets } from '@/services/server/secrets';
import { getStorages } from '@/services/server/storages';

import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';
import { doesStorageDataNeedToBeRefreshed } from '@/utils/app/storages';
import { authOptions } from '@/utils/server/auth';
import { isSecretActioning } from '@/utils/app/secrets';

import { ActionFieldHintType } from '@/types/enums/data-table';
import { ProjectStatus } from '@/types/enums/projects';
import { ProjectSecretStatus, SecretScope } from '@/types/enums/secrets';
import { Project } from '@/types/projects';
import { Secret, SecretsResponse } from '@/types/secrets';
import { StoragesResponse } from '@/types/storages';

import { AddSecret, AssignSecret } from '@/components/features/secrets';
import DeleteSecretModal from '@/components/features/secrets/DeleteSecretModal';
import { SecretsPageContent } from '@/components/features/secrets/SecretsPageContent';
import { ActionButton } from '@/components/shared/Buttons';

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
        doesStorageDataNeedToBeRefreshed(query.state.data.storages)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  // State management at page level
  const [targetSecret, setTargetSecret] = useState<Secret | null>(null);

  const checkSecretIsAttachedToStorage = useCallback(
    (s: Secret) => {
      return storagesData?.storages.some(
        (storage) => storage.secretId === s.id,
      );
    },
    [storagesData],
  );

  const checkSecretIsOrganizationScoped = useCallback((s: Secret) => {
    return s.scope !== SecretScope.ORGANIZATION;
  }, []);

  const checkDeleteDisabled = useCallback(
    (s: Secret) => {
      return isSecretActioning(s) || checkSecretIsAttachedToStorage(s);
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
        key: 'edit',
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
          {
            showHint: isSecretActioning,
            message: t('list.actions.delete.hint.actionPending'),
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
        .map((ps) => ps.projectId) ?? [],
    [targetSecret],
  );

  const addButton = (
    <ActionButton primary onPress={onAddSecretFormOpenChange}>
      {t('actions.add')}
    </ActionButton>
  );

  const additionalModals = (
    <>
      <AddSecret
        isOpen={isAddSecretFormOpen}
        onClose={onClose}
        secrets={secrets.secrets}
        projects={projects}
        disabledProjectIds={projectsNotReadyIds}
      />
      <AssignSecret
        isOpen={isAssignSecretFormOpen}
        onClose={onAssignSecretFormOpenChange}
        projects={projects}
        secret={targetSecret}
        selectedProjectIds={
          targetSecret?.projectSecrets.map((ps) => ps.projectId) ?? []
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

  return (
    <SecretsPageContent
      initialSecrets={secrets}
      showScopeColumn={true}
      showAddButton={true}
      additionalActions={addButton}
      additionalModals={additionalModals}
      actions={actions}
    />
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
      ...(await serverSideTranslations(locale, ['common', 'secrets'])),
      projects: projects?.projects || [],
      secrets,
      storages,
    },
  };
}
