// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Select,
  SelectItem,
  SelectSection,
  useDisclosure,
} from '@heroui/react';
import { IconUserPlus, IconX } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { Trans, useTranslation } from 'next-i18next';
import { useSession } from 'next-auth/react';
import useSystemToast from '@/hooks/useSystemToast';

import {
  addUsersToProject as addUsersToProjectAPI,
  deleteUserFromProject as deleteUserFromProjectAPI,
} from '@/services/app/projects';
import { fetchInvitedUsers, fetchUsers } from '@/services/app/users';

import {
  getCandidateInvitedUsersForProject,
  getCandidateUsersForProject,
} from '@/utils/app/projects';
import { displayTimestamp } from '@/utils/app/strings';

import { TableColumns } from '@/types/data-table/clientside-table';
import { ProjectUsersTableField } from '@/types/enums/project-users-table-fields';
import { FormField } from '@/types/forms/forms';
import {
  InviteMemberFormData,
  ProjectWithMembers,
  UserInProject,
} from '@/types/projects';
import { InvitedUsersResponse, UsersResponse } from '@/types/users';
import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import DrawerForm from '@/components/shared/Drawer/DrawerForm';
import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';
import { ZodType, z } from 'zod';
import { SortDirection } from '@/types/enums/sort-direction';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { compareUsersByFullName } from '@/utils/app/users';
import { getFilteredData } from '@/utils/app/data-table';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { FilterComponentType } from '@/types/enums/filters';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';
import { ActionButton } from '@/components/shared/Buttons';
interface Props {
  project: ProjectWithMembers;
}

const translationSet = 'projects';

const columns: TableColumns<ProjectUsersTableField | null> = [
  {
    key: ProjectUsersTableField.NAME,
    sortable: true,
  },
  {
    key: ProjectUsersTableField.EMAIL,
    sortable: true,
  },
  { key: ProjectUsersTableField.ROLE, sortable: true },
  { key: ProjectUsersTableField.LAST_ACTIVE, sortable: true },
];

const customComparator: CustomComparatorConfig<
  UserInProject,
  ProjectUsersTableField
> = {
  [ProjectUsersTableField.NAME]: compareUsersByFullName,
};

const filterableFields: (keyof UserInProject)[] = [
  'firstName',
  'lastName',
  'email',
]; // Logical OR search of all fields

export const Members: React.FC<Props> = ({ project }) => {
  const { t } = useTranslation(translationSet);
  const { toast } = useSystemToast();
  const { data: session, update } = useSession();

  const {
    isOpen: isAddUserOpen,
    onOpen: onAddUserOpen,
    onOpenChange: onAddUserOpenChange,
  } = useDisclosure();

  const {
    isOpen: isRemoveConfirmOpen,
    onOpen: onRemoveConfirmOpen,
    onOpenChange: onRemoveConfirmOpenChange,
  } = useDisclosure();

  const [filter, setFilter] = useState<ClientSideDataFilter<UserInProject>[]>(
    [],
  );

  const filteredUsersData = useMemo(() => {
    return getFilteredData(project.users, filter);
  }, [filter, project.users]);

  const queryClient = useQueryClient();
  const [userBeingRemoved, setUserBeingRemoved] = useState<UserInProject>();

  const {
    data: users,
    isFetching,
    isRefetching,
    refetch,
    dataUpdatedAt,
  } = useQuery<UsersResponse>({
    queryKey: ['users'],
    queryFn: fetchUsers,
  });

  const { data: invitedUsers } = useQuery<InvitedUsersResponse>({
    queryKey: ['invited-users'],
    queryFn: fetchInvitedUsers,
  });

  const candidateUsers = useMemo(() => {
    return getCandidateUsersForProject(project, users?.data);
  }, [project, users]);

  const candidateInvitedUsers = useMemo(() => {
    return getCandidateInvitedUsersForProject(project, invitedUsers?.data);
  }, [project, invitedUsers]);

  const customRenderers: Partial<
    Record<
      ProjectUsersTableField,
      (item: UserInProject) => React.ReactNode | string
    >
  > = {
    [ProjectUsersTableField.NAME]: (item) =>
      `${item.firstName} ${item.lastName}`,
    [ProjectUsersTableField.LAST_ACTIVE]: (item) => {
      if (item.lastActiveAt) {
        return displayTimestamp(new Date(item.lastActiveAt));
      }
      return '-';
    },
  };

  const formSchema: ZodType<InviteMemberFormData> = useMemo(
    () =>
      z.object({
        users: z
          .string()
          .nonempty(
            t(
              'settings.membersAndInvitedUsers.members.actions.add.validation.users.selected',
            ) || '',
          )
          .or(z.array(z.string()))
          .refine(
            (value) =>
              (typeof value === 'string' && value.trim() !== '') ||
              (Array.isArray(value) && value.length > 0),
            {
              message:
                t(
                  'settings.membersAndInvitedUsers.members.actions.add.validation.users.selected',
                ) || '',
            },
          ),
      }),
    [t],
  );

  const formFields: FormField<InviteMemberFormData>[] = [
    {
      name: 'users',
      label: t(
        'settings.membersAndInvitedUsers.members.actions.add.form.users.label',
      ),
      placeholder: t(
        'settings.membersAndInvitedUsers.members.actions.add.form.users.placeholder',
      ),
      isRequired: true,
      component: (props) => (
        <Select
          aria-label={props.label}
          variant="bordered"
          defaultSelectedKeys={[props.defaultValue]}
          {...props}
          selectionMode="multiple"
          renderValue={(items) => `${items.length} selected`}
          startContent={<IconUserPlus size={18} />}
        >
          {!!candidateUsers.length && (
            <SelectSection
              showDivider={!!candidateInvitedUsers.length}
              title={
                t(
                  'settings.membersAndInvitedUsers.members.actions.add.form.users.section.users',
                )!
              }
            >
              {candidateUsers.map((u) => (
                <SelectItem key={u.id}>{u.email}</SelectItem>
              ))}
            </SelectSection>
          )}
          {!!candidateInvitedUsers.length && (
            <SelectSection
              title={
                t(
                  'settings.membersAndInvitedUsers.members.actions.add.form.users.section.invitedUsers',
                )!
              }
            >
              {candidateInvitedUsers.map((u) => (
                <SelectItem key={u.id}>{u.email}</SelectItem>
              ))}
            </SelectSection>
          )}
        </Select>
      ),
    },
  ];

  const {
    mutate: deleteUserFromProject,
    isPending: isDeletingUserFromProject,
  } = useMutation({
    mutationFn: deleteUserFromProjectAPI,
    onSuccess: (data, variables) => {
      onRemoveConfirmOpenChange();
      toast.success(
        t(
          'settings.membersAndInvitedUsers.members.actions.remove.notification.success',
        ),
      );
      queryClient.invalidateQueries({ queryKey: ['project'] });

      const currentUser = users?.data.find(
        (u) => u.email === session?.user?.email,
      );
      const currentUserId = currentUser?.id;

      if (currentUserId && variables.userId === currentUserId) {
        console.log(
          'Current user removed themselves from project, refreshing token...',
        );
        update();
      } else {
        console.log('Current user not being changed, skipping token refresh');
      }
    },
    onError: () => {
      toast.error(
        t(
          'settings.membersAndInvitedUsers.members.actions.remove.notification.error',
        ),
      );
    },
  });

  const { mutate: addUsersToProject, isPending: isAddingUsersToProject } =
    useMutation({
      mutationFn: addUsersToProjectAPI,
      onSuccess: (data, variables) => {
        onAddUserOpenChange();
        toast.success(
          t(
            'settings.membersAndInvitedUsers.members.actions.add.notification.success',
          ),
        );

        queryClient.invalidateQueries({ queryKey: ['project'] });

        const currentUser = users?.data.find(
          (u) => u.email === session?.user?.email,
        );
        const currentUserId = currentUser?.id;

        if (currentUserId && variables.userIds.includes(currentUserId)) {
          console.log(
            'Current user added themselves to project, refreshing token...',
          );
          update();
        } else {
          console.log('Current user not found, skipping token refresh');
        }
      },
      onError: () => {
        toast.error(
          t(
            'settings.membersAndInvitedUsers.members.actions.add.notification.error',
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

  const actions = () => {
    return [
      {
        key: 'Remove user',
        label: t(
          'settings.membersAndInvitedUsers.members.actions.remove.label',
        ),
        color: 'danger',
        startContent: <IconX />,
        onPress: (user: UserInProject) => {
          setUserBeingRemoved(user);
          onRemoveConfirmOpen();
        },
      },
    ];
  };

  const handleSearchFilter = useCallback(
    (filter: FilterValueMap) => {
      if (
        filter.search &&
        !(
          Array.isArray(filter.search) &&
          filter.search.length === 1 &&
          filter.search[0] === ''
        )
      ) {
        setFilter([
          {
            values: filter.search,
            compositeFields: filterableFields.map((field) => ({ field })),
          },
        ]);
      } else {
        setFilter([]);
      }
    },
    [setFilter],
  );

  const filterConfig = {
    search: {
      name: 'search',
      label: t('list.filter.search.placeholder'),
      placeholder: t('list.filter.search.placeholder'),
      type: FilterComponentType.TEXT,
    },
  };

  return (
    <div>
      <div className="flex flex-col">
        <h3>{t('settings.membersAndInvitedUsers.members.title')}</h3>
        <ActionsToolbar
          filterConfig={filterConfig}
          onFilterChange={handleSearchFilter}
          onRefresh={refetch}
          updatedTimestamp={dataUpdatedAt}
          endContent={
            <ActionButton
              primary
              aria-label={
                t('settings.membersAndInvitedUsers.members.actions.add') || ''
              }
              isDisabled={
                candidateUsers.length === 0 &&
                candidateInvitedUsers.length === 0
              }
              onPress={onAddUserOpen}
            >
              {t('settings.membersAndInvitedUsers.members.actions.add.title')}
            </ActionButton>
          }
        />
        <div className="mt-4 pb-8">
          {project.users.length ? (
            <ClientSideDataTable
              data={filteredUsersData}
              columns={columns}
              rowActions={actions}
              defaultSortByField={ProjectUsersTableField.NAME}
              defaultSortDirection={SortDirection.ASC}
              customRenderers={customRenderers}
              customComparator={customComparator}
              translation={t}
              idKey="id"
              translationKeyPrefix="users"
              isFetching={isFetching || isRefetching}
              isLoading={isDeletingUserFromProject}
            />
          ) : (
            <h4>{t('settings.membersAndInvitedUsers.members.empty')}</h4>
          )}
        </div>
      </div>
      <DrawerForm<InviteMemberFormData>
        isOpen={isAddUserOpen}
        isActioning={isAddingUsersToProject}
        validationSchema={formSchema}
        title={t(
          'settings.membersAndInvitedUsers.members.actions.add.modal.title',
        )}
        cancelText={t(
          'settings.membersAndInvitedUsers.members.actions.add.modal.cancel',
        )}
        confirmText={t(
          'settings.membersAndInvitedUsers.members.actions.add.modal.confirm',
        )}
        onFormSuccess={(values) => {
          const users = values.users;
          const userIds =
            typeof users === 'string'
              ? users.split(',').filter((id) => id.trim() !== '')
              : [];
          addUsersToProject({ projectId: project.id, userIds: userIds });
        }}
        onCancel={onAddUserOpenChange}
        renderFields={(form) => {
          return (
            <div className="flex flex-col gap-4">
              <Trans parent="p">
                {t(
                  'settings.membersAndInvitedUsers.members.actions.add.modal.intro',
                  {
                    project: project.name,
                  },
                )}
              </Trans>
              {formFields.map((field) => (
                <FormFieldComponent<InviteMemberFormData>
                  key={field.name}
                  formField={field}
                  errorMessage={form.formState.errors[field.name]?.message}
                  register={form.register}
                />
              ))}
            </div>
          );
        }}
      />
      <ConfirmationModal
        description={t(
          'settings.membersAndInvitedUsers.members.actions.remove.description',
          {
            firstName: userBeingRemoved?.firstName,
            lastName: userBeingRemoved?.lastName,
            project: project.name,
          },
        )}
        title={t(
          'settings.membersAndInvitedUsers.members.actions.remove.confirm',
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

export default Members;
