// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tooltip, useDisclosure } from '@heroui/react';
import { IconX } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { Trans, useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { fetchOrganization } from '@/services/app/organizations';
import { deleteUserFromProject as deleteUserFromProjectAPI } from '@/services/app/projects';

import { TableColumns } from '@/types/data-table/clientside-table';
import { ProjectUsersTableField } from '@/types/enums/project-users-table-fields';
import { InvitedUserInProject, ProjectWithMembers } from '@/types/projects';

import InviteUserModal from '@/components/features/users/InviteUserModal';
import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  project: ProjectWithMembers;
}

const translationSet = 'projects';

export const InvitedUsers: React.FC<Props> = ({ project }) => {
  const { t } = useTranslation(translationSet);
  const { toast } = useSystemToast();

  const columns: TableColumns<ProjectUsersTableField | null> = [
    {
      key: ProjectUsersTableField.EMAIL,
      sortable: true,
    },
    { key: ProjectUsersTableField.ROLE, sortable: true },
  ];

  const actions = () => {
    return [
      {
        key: 'Remove user',
        label: t(
          'settings.membersAndInvitedUsers.invitedUsers.actions.remove.label',
        ),
        color: 'danger',
        startContent: <IconX />,
        onPress: (user: InvitedUserInProject) => {
          setUserBeingRemoved(user);
          onRemoveConfirmOpen();
        },
      },
    ];
  };

  const {
    isOpen: isInviteUserOpen,
    onOpen: onInviteUserOpen,
    onOpenChange: onInviteUserOpenChange,
  } = useDisclosure();

  const {
    isOpen: isRemoveConfirmOpen,
    onOpen: onRemoveConfirmOpen,
    onOpenChange: onRemoveConfirmOpenChange,
  } = useDisclosure();

  const queryClient = useQueryClient();
  const [userBeingRemoved, setUserBeingRemoved] =
    useState<InvitedUserInProject>();

  // Fetch organization identity provider status
  const { data: organizationData, isLoading: isLoadingOrgData } = useQuery({
    queryKey: ['organization'],
    queryFn: fetchOrganization,
  });

  const {
    mutate: deleteUserFromProject,
    isPending: isDeletingUserFromProject,
  } = useMutation({
    mutationFn: deleteUserFromProjectAPI,
    onSuccess: () => {
      onRemoveConfirmOpenChange();
      toast.success(
        t(
          'settings.membersAndInvitedUsers.invitedUsers.actions.remove.notification.success',
        ),
      );
      queryClient.invalidateQueries({ queryKey: ['project'] });
    },
    onError: () => {
      toast.error(
        t(
          'settings.membersAndInvitedUsers.invitedUsers.actions.remove.notification.error',
        ),
      );
    },
  });

  const handleRemoveUserFromProject = useCallback(() => {
    if (project.id && userBeingRemoved?.id) {
      deleteUserFromProject({
        userId: userBeingRemoved.id,
        projectId: project.id,
      });
    }
  }, [deleteUserFromProject, project.id, userBeingRemoved]);

  return (
    <div>
      <div className="flex justify-between gap-4">
        <h3>{t('settings.membersAndInvitedUsers.invitedUsers.title')}</h3>
        <Tooltip
          content={t('settings.membersAndInvitedUsers.invitedUsers.disabled')}
          isDisabled={!organizationData?.idpLinked}
        >
          <span>
            <ActionButton
              secondary
              aria-label={
                t('settings.membersAndInvitedUsers.invitedUsers.actions.add') ||
                ''
              }
              onPress={onInviteUserOpen}
              isDisabled={!!organizationData?.idpLinked || isLoadingOrgData}
            >
              {t(
                'settings.membersAndInvitedUsers.invitedUsers.actions.add.title',
              )}
            </ActionButton>
          </span>
        </Tooltip>
      </div>
      <div className="mt-4 pb-8">
        {!!project.invitedUsers.length ? (
          <ClientSideDataTable
            data={project.invitedUsers}
            columns={columns}
            rowActions={actions}
            defaultSortByField={ProjectUsersTableField.EMAIL}
            translation={t}
            idKey="id"
            translationKeyPrefix="users"
            isLoading={isDeletingUserFromProject}
          />
        ) : (
          <h4>{t('settings.membersAndInvitedUsers.invitedUsers.empty')}</h4>
        )}
      </div>
      <InviteUserModal
        isOpen={isInviteUserOpen}
        onOpenChange={onInviteUserOpenChange}
        selectedProjectIds={[project.id]}
      />
      <ConfirmationModal
        description={
          <Trans parent="span">
            {t(
              'settings.membersAndInvitedUsers.invitedUsers.actions.remove.description',
              {
                email: userBeingRemoved?.email,
                project: project.name,
              },
            )}
          </Trans>
        }
        title={t(
          'settings.membersAndInvitedUsers.invitedUsers.actions.remove.confirm',
        )}
        isOpen={isRemoveConfirmOpen}
        loading={isDeletingUserFromProject}
        onConfirm={handleRemoveUserFromProject}
        onClose={onRemoveConfirmOpenChange}
        confirmationButtonColor="danger"
      />
    </div>
  );
};

export default InvitedUsers;
