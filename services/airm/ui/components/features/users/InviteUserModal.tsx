// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React, { useMemo } from 'react';

import { Select, SelectItem } from '@heroui/react';
import { IconAt } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useTranslation } from 'next-i18next';

import { useAccessControl } from '@/hooks/useAccessControl';
import { useSystemToast } from '@/hooks/useSystemToast';

import { fetchProjects } from '@/services/app/projects';
import {
  fetchInvitedUsers,
  fetchUsers,
  inviteUser as inviteUserAPI,
} from '@/services/app/users';

import { APIRequestError } from '@/utils/app/errors';

import { UserRole } from '@/types/enums/user-roles';
import { FormField } from '@/types/forms/forms';
import { ProjectsResponse } from '@/types/projects';
import {
  InvitedUser,
  InviteUserFormData,
  InviteUserRequest,
  InvitedUsersResponse,
  User,
  UsersResponse,
} from '@/types/users';

import { DrawerForm } from '@/components/shared/Drawer';
import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';
import FormPasswordInput from '@/components/shared/ManagedForm/FormPasswordInput';

import { ZodType, z } from 'zod';

interface Props {
  isOpen: boolean;
  selectedProjectIds?: string[];
  onOpenChange: () => void;
  onSuccess?: () => void;
  invitedUsersInitialData?: InvitedUsersResponse;
  usersInitialData?: UsersResponse;
}

const InviteUserModal: React.FC<Props> = ({
  isOpen,
  onOpenChange,
  selectedProjectIds,
  onSuccess,
  invitedUsersInitialData,
  usersInitialData,
}) => {
  const i18nKeySet = 'users';
  const { t } = useTranslation(i18nKeySet);
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();
  const { isTempPasswordRequired } = useAccessControl();

  const { data: userData } = useQuery<UsersResponse>({
    queryKey: ['users'],
    queryFn: fetchUsers,
    initialData: usersInitialData,
  });

  const { data: invitedUserData } = useQuery<InvitedUsersResponse>({
    queryKey: ['invited-users'],
    queryFn: fetchInvitedUsers,
    initialData: invitedUsersInitialData,
  });

  const { data: projectData } = useQuery<ProjectsResponse>({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  });

  const allUsers = useMemo(
    () => [...(userData?.data || []), ...(invitedUserData?.data || [])],
    [userData, invitedUserData],
  );

  const allProjects = useMemo(() => projectData?.projects || [], [projectData]);

  const formSchema: ZodType<InviteUserFormData> = useMemo(
    () =>
      z.object({
        email: z
          .string()
          .nonempty(t('modal.addUser.form.email.validation.required') || '')
          .email(t('modal.addUser.form.email.validation.format') || '')
          .refine(
            (value) => {
              if (
                allUsers.some(
                  (user: User | InvitedUser) =>
                    user.email.toLowerCase() ===
                    (value as string).trim().toLowerCase(),
                )
              ) {
                return false;
              }
              return true;
            },
            {
              message: t('modal.addUser.form.email.validation.unique') || '',
            },
          ),
        projectIds: z
          .string()
          .optional()
          .transform((val) => (val ? val.split(',') : [])),
        roles: z
          .string()
          .nonempty(t('modal.addUser.form.roles.validation.selected') || ''),
        tempPassword: z
          .union([
            z
              .string()
              .min(
                8,
                t('modal.addUser.form.tempPassword.validation.minLength') || '',
              )
              .max(
                256,
                t('modal.addUser.form.tempPassword.validation.maxLength') || '',
              ),
            z.literal(''), // allow empty string = "no temp password"
          ])
          .optional(),
      }),
    [t, allUsers],
  );

  const { mutate: inviteUser, isPending: isInvitingUser } = useMutation<
    User,
    Error,
    InviteUserRequest
  >({
    mutationFn: inviteUserAPI,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['invited-users'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['project'] });
      toast.success(t('modal.addUser.notification.success'));
      onOpenChange();

      if (onSuccess) {
        onSuccess();
      }
    },
    onError: (error) => {
      toast.error(
        t('modal.addUser.notification.error'),
        error as APIRequestError,
      );

      console.error('Error inviting user:', error);
    },
  });

  const formContent: FormField<InviteUserFormData>[] = useMemo(
    () => [
      {
        name: 'email',
        label: t('modal.addUser.form.email.label'),
        isRequired: true,
        icon: (props) => <IconAt size="14" {...props} />,
      },
      {
        name: 'roles',
        label: t('modal.addUser.form.roles.label'),
        isRequired: true,
        component: (formElemProps) => (
          <Select
            labelPlacement="outside"
            placeholder={t('modal.addUser.form.roles.placeholder')}
            variant="bordered"
            {...formElemProps}
            defaultSelectedKeys={[UserRole.PLATFORM_ADMIN]}
            disallowEmptySelection
          >
            <SelectItem key={UserRole.PLATFORM_ADMIN}>
              {t('modal.addUser.form.roles.options.platformAdmin')}
            </SelectItem>
            <SelectItem key={UserRole.TEAM_MEMBER}>
              {t('modal.addUser.form.roles.options.teamMember')}
            </SelectItem>
          </Select>
        ),
      },
      {
        name: 'projectIds',
        label: t('modal.addUser.form.projects.label'),
        placeholder: t('modal.addUser.form.projects.placeholder'),
        isRequired: false,
        component: (formElemProps) => (
          <Select
            data-testid="project-select"
            labelPlacement="outside"
            selectionMode="multiple"
            defaultSelectedKeys={selectedProjectIds || []}
            variant="bordered"
            {...formElemProps}
          >
            {allProjects.map((project: any) => (
              <SelectItem
                key={project.id}
                data-testid={`project-${project.id}`}
              >
                {project.name}
              </SelectItem>
            ))}
          </Select>
        ),
      },
    ],
    [t, allProjects, selectedProjectIds],
  );

  return (
    <DrawerForm<InviteUserFormData>
      isOpen={isOpen}
      isActioning={isInvitingUser}
      title={t('modal.addUser.title')}
      onOpenChange={onOpenChange}
      onFormSuccess={(data) => {
        inviteUser({
          email: data.email,
          roles:
            data.roles === UserRole.PLATFORM_ADMIN
              ? [UserRole.PLATFORM_ADMIN]
              : [],
          project_ids: data.projectIds,
          temporary_password: data.tempPassword,
        } as InviteUserRequest);
      }}
      defaultValues={{
        email: '',
        roles: UserRole.PLATFORM_ADMIN,
      }}
      validationSchema={formSchema}
      renderFields={(form) => (
        <div className="flex flex-col gap-4">
          {formContent.map((field) => (
            <FormFieldComponent<InviteUserFormData>
              key={field.name}
              formField={field}
              errorMessage={form.formState.errors[field.name]?.message}
              register={form.register}
            />
          ))}
          {isTempPasswordRequired && (
            <FormPasswordInput
              form={form}
              name="tempPassword"
              label={t('modal.addUser.form.tempPassword.label')}
              placeholder={t('modal.addUser.form.tempPassword.placeholder')}
              isRequired
            />
          )}
          <p className="text-small">{t('modal.addUser.instruction')}</p>
        </div>
      )}
      onCancel={onOpenChange}
      cancelText={t('modal.addUser.actions.cancel')}
      confirmText={t('modal.addUser.actions.confirm')}
    />
  );
};

export default InviteUserModal;
