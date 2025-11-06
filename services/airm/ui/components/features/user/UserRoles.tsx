// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem, useDisclosure } from '@heroui/react';
import { IconUser } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';
import { useAccessControl } from '@/hooks/useAccessControl';

import { assignRoleToUser as assignRoleToUserAPI } from '@/services/app/users';

import { APIRequestError } from '@/utils/app/errors';

import { UserRole } from '@/types/enums/user-roles';
import { FormField } from '@/types/forms/forms';
import { AssignUserRoleFormData, User } from '@/types/users';

import { DrawerForm } from '@/components/shared/DrawerForm';
import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';
import { ActionButton } from '@/components/shared/Buttons';
import ProjectAndRoleEntry from './ProjectAndRoleEntry';

import { ZodType, z } from 'zod';

interface Props {
  user: User;
}

const translationSet = 'users';
export const UserRoles: React.FC<Props> = ({ user }) => {
  const { t } = useTranslation(translationSet);
  const { toast } = useSystemToast();
  const { isOpen, onOpen, onOpenChange } = useDisclosure();
  const queryClient = useQueryClient();
  const { isRoleManagementEnabled } = useAccessControl();

  const { mutate: assignRoleToUser, isPending } = useMutation({
    mutationFn: assignRoleToUserAPI,
    onSuccess: () => {
      onOpenChange();
      queryClient.invalidateQueries({ queryKey: ['user'] });
      toast.success(t('detail.projectsAndRoles.roles.notification.success'));
    },
    onError: (error) => {
      toast.error(
        t('detail.projectsAndRoles.roles.notification.error'),
        error as APIRequestError,
      );
      console.error('Error assigning role to user:', error);
    },
  });

  const createQuotaFormSchema: ZodType<AssignUserRoleFormData> = useMemo(
    () =>
      z.object({
        role: z
          .string()
          .nonempty(
            t('detail.projectsAndRoles.roles.form.role.selected') || '',
          ),
      }),
    [t],
  );

  const formFields: FormField<AssignUserRoleFormData>[] = [
    {
      name: 'role',
      label: t('detail.projectsAndRoles.roles.form.role.label'),
      placeholder: t('detail.projectsAndRoles.projects.form.role.placeholder'),
      component: (props) => (
        <Select
          aria-label={props.label}
          variant="bordered"
          defaultSelectedKeys={[props.defaultValue]}
          disallowEmptySelection
          {...props}
        >
          <SelectItem key={UserRole.PLATFORM_ADMIN}>
            {t('detail.projectsAndRoles.roles.form.role.options.platformAdmin')}
          </SelectItem>
          <SelectItem key={UserRole.TEAM_MEMBER}>
            {t('detail.projectsAndRoles.roles.form.role.options.teamMember')}
          </SelectItem>
        </Select>
      ),
    },
  ];

  return (
    <div>
      <div className="mt-8 flex justify-between gap-4">
        <h3 className="uppercase">
          {t('detail.projectsAndRoles.roles.title')}
        </h3>
        {isRoleManagementEnabled && (
          <ActionButton
            tertiary
            aria-label={t('detail.projectsAndRoles.roles.actions.edit') || ''}
            color="primary"
            size="sm"
            onPress={onOpen}
          >
            {t('detail.projectsAndRoles.roles.actions.edit.title')}
          </ActionButton>
        )}
      </div>
      <div className="mt-4">
        {user.role === UserRole.PLATFORM_ADMIN ? (
          <ProjectAndRoleEntry
            name={t(
              'detail.projectsAndRoles.roles.options.platformAdministrator.name',
            )}
            description={t(
              'detail.projectsAndRoles.roles.options.platformAdministrator.description',
            )}
            icon={IconUser}
          />
        ) : (
          <ProjectAndRoleEntry
            name={t('detail.projectsAndRoles.roles.options.teamMember.name')}
            description={t(
              'detail.projectsAndRoles.roles.options.teamMember.description',
            )}
            icon={IconUser}
          />
        )}
      </div>
      <DrawerForm<AssignUserRoleFormData>
        isOpen={isOpen}
        isActioning={isPending}
        title={t('detail.projectsAndRoles.roles.actions.edit.title')}
        cancelText={t('detail.projectsAndRoles.roles.actions.edit.cancel')}
        confirmText={t('detail.projectsAndRoles.roles.actions.edit.confirm')}
        validationSchema={createQuotaFormSchema}
        defaultValues={{ role: user.role }}
        onFormSuccess={(data: { [x: string]: unknown }) => {
          const role = data['role'] as UserRole;
          assignRoleToUser({ userId: user.id, role });
        }}
        onCancel={onOpenChange}
        renderFields={(form) => (
          <>
            {formFields.map((field) => (
              <FormFieldComponent<AssignUserRoleFormData>
                key={field.name as string}
                formField={{
                  name: field.name as keyof AssignUserRoleFormData,
                  label: field.label,
                  placeholder: field.placeholder,
                  isRequired: field.isRequired,
                  description: field.description,
                  component: field.component,
                }}
                errorMessage={
                  form.formState.errors[
                    field.name as keyof AssignUserRoleFormData
                  ]?.message
                }
                register={form.register}
                defaultValue={user.role}
              />
            ))}
          </>
        )}
      />
    </div>
  );
};

export default UserRoles;
