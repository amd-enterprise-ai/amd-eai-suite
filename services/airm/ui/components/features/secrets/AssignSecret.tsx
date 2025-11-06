// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem } from '@heroui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { updateSecretAssignment } from '@/services/app/secrets';

import { APIRequestError } from '@/utils/app/errors';

import { FormField } from '@/types/forms/forms';
import { Project } from '@/types/projects';
import { AssignSecretFormData, Secret } from '@/types/secrets';

import { DrawerForm } from '@/components/shared/DrawerForm';
import { FormFieldComponent } from '@/components/shared/ManagedForm/FormFieldComponent';

import { z } from 'zod';

interface Props {
  isOpen: boolean;
  secret: Secret | null;
  project?: Project;
  projects: Project[];
  selectedProjectIds: string[];
  disabledProjectIds: string[];
  onClose: () => void;
}

export const AssignSecret: React.FC<Props> = ({
  isOpen,
  project,
  projects,
  secret,
  selectedProjectIds,
  disabledProjectIds = [],
  onClose,
}) => {
  const { t } = useTranslation('secrets');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const { mutate: updateAssignment, isPending } = useMutation({
    mutationFn: async (data: AssignSecretFormData) => {
      if (!secret) {
        throw new Error('Secret is null');
      }
      return updateSecretAssignment(secret.id, {
        project_ids: data.projectIds,
      });
    },
    onSuccess: () => {
      toast.success(t('form.assign.notification.success'));
      queryClient.invalidateQueries({
        queryKey: project?.id ? ['secrets', project?.id] : ['secrets'],
      });
      onClose();
    },
    onError: (error) => {
      toast.error(
        t('form.assign.notification.error'),
        error as APIRequestError,
      );
    },
  });

  const formSchema = useMemo(
    () =>
      z.object({
        projectIds: z.preprocess((val: unknown) => {
          if (Array.isArray(val)) return val as string[];
          if (typeof val === 'string' && val !== '') return val.split(',');
          return [];
        }, z.array(z.string())),
      }) as z.ZodType<AssignSecretFormData>,
    [],
  );

  const handleFormSubmit = useCallback(
    async (data: AssignSecretFormData): Promise<void> => {
      updateAssignment(data);
    },
    [updateAssignment],
  );

  const formContent: FormField<AssignSecretFormData>[] = [
    {
      name: 'projectIds',
      label: t('form.assign.field.projectIds.label'),
      placeholder: t('form.assign.field.projectIds.placeholder'),
      isRequired: false,
      component: (formElemProps) => (
        <Select
          labelPlacement="outside"
          selectionMode="multiple"
          defaultSelectedKeys={selectedProjectIds || []}
          disabledKeys={disabledProjectIds}
          variant="bordered"
          {...formElemProps}
        >
          {projects.map((project: Project) => {
            return <SelectItem key={project.id}>{project.name}</SelectItem>;
          })}
        </Select>
      ),
    },
  ];

  if (!secret) return null;

  return (
    <DrawerForm<AssignSecretFormData>
      isOpen={isOpen}
      isActioning={isPending}
      onFormSuccess={(values) => {
        handleFormSubmit({
          projectIds: values.projectIds,
        });
      }}
      onCancel={onClose}
      title={t('form.assign.title')}
      confirmText={t('form.assign.action.save')}
      cancelText={t('form.assign.action.cancel')}
      renderFields={(form) => (
        <div className="flex flex-col gap-4">
          {formContent.map((field) => (
            <FormFieldComponent<AssignSecretFormData>
              key={field.name}
              formField={field}
              errorMessage={form.formState.errors[field.name]?.message}
              register={form.register}
            />
          ))}
        </div>
      )}
      validationSchema={formSchema}
    />
  );
};

export default AssignSecret;
