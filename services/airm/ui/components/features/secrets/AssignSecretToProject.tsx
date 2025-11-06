// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Select, SelectItem } from '@heroui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { assignSecretToProject } from '@/services/app/secrets';

import { displayTimestamp } from '@/utils/app/strings';
import { APIRequestError } from '@/utils/app/errors';

import { FormField } from '@/types/forms/forms';
import { Project } from '@/types/projects';
import { AssignSecretToProjectFormData, Secret } from '@/types/secrets';

import { DrawerForm } from '@/components/shared/DrawerForm';
import { FormFieldComponent } from '@/components/shared/ManagedForm/FormFieldComponent';

import { SecretStatus } from './SecretStatus';

import { z } from 'zod';
import SecretProjectAssignedTo from './SecretProjectAssignedTo';
import { NoDataDisplay } from '@/components/shared/DataTable';

interface Props {
  isOpen: boolean;
  availableSecrets: Secret[];
  project: Project;
  onClose: () => void;
}

export const AssignSecretToProject: React.FC<Props> = ({
  isOpen,
  availableSecrets = [],
  project,
  onClose,
}) => {
  const { t } = useTranslation('secrets');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const secretsById = useMemo(() => {
    const map = new Map<string, Secret>();
    for (const s of availableSecrets ?? []) map.set(s.id, s);
    return map;
  }, [availableSecrets]);

  const { mutate: updateAssignment, isPending } = useMutation({
    mutationFn: async (data: AssignSecretToProjectFormData) => {
      if (!project) {
        throw new Error('Project is null');
      }

      return assignSecretToProject(project.id, data.secretId);
    },
    onSuccess: () => {
      toast.success(t('form.assignSecretToProject.notification.success'));
      if (project) {
        queryClient.invalidateQueries({ queryKey: ['secrets', project.id] });
        queryClient.invalidateQueries({
          queryKey: ['projectSecrets', project.id],
        });
      }
      queryClient.invalidateQueries({ queryKey: ['secrets'] });
      onClose();
    },
    onError: (error) => {
      toast.error(
        t('form.assignSecretToProject.notification.error'),
        error as APIRequestError,
      );
    },
  });

  const formSchema = useMemo(
    () =>
      z.object({
        secretId: z
          .string()
          .min(1, t('form.assignSecretToProject.field.secretId.required')),
      }) as z.ZodType<AssignSecretToProjectFormData>,
    [t],
  );

  const handleFormSubmit = useCallback(
    async (data: AssignSecretToProjectFormData): Promise<void> => {
      updateAssignment(data);
    },
    [updateAssignment],
  );

  const formContent: FormField<AssignSecretToProjectFormData>[] = [
    {
      name: 'secretId',
      label: t('form.assignSecretToProject.field.secretId.label'),
      placeholder: t('form.assignSecretToProject.field.secretId.placeholder'),
      isRequired: true,
      component: (formElemProps) => (
        <Select selectionMode="single" variant="bordered" {...formElemProps}>
          {availableSecrets.map((secret: Secret) => {
            return <SelectItem key={secret.id}>{secret.name}</SelectItem>;
          })}
        </Select>
      ),
    },
  ];

  if (!project) return null;

  return (
    <DrawerForm<AssignSecretToProjectFormData>
      isOpen={isOpen}
      isActioning={isPending}
      onFormSuccess={(values) => {
        handleFormSubmit({
          secretId: values.secretId,
        });
      }}
      onCancel={onClose}
      title={t('form.assignSecretToProject.title')}
      confirmText={t('form.assignSecretToProject.action.save')}
      cancelText={t('form.assignSecretToProject.action.cancel')}
      renderFields={(form) => {
        const selectedId = form.watch('secretId');
        const selectedSecret = selectedId
          ? secretsById.get(selectedId)
          : undefined;

        return (
          <div className="flex flex-col gap-4">
            {formContent.map((field) => (
              <FormFieldComponent<AssignSecretToProjectFormData>
                key={field.name}
                formField={field}
                errorMessage={form.formState.errors[field.name]?.message}
                register={form.register}
              />
            ))}
            <hr />
            <section>
              <h4 className="mb-3">
                {t('form.assignSecretToProject.details.title')}
              </h4>
              <div className="grid grid-cols-1 gap-y-4">
                <div className="flex flex-col">
                  <span className="text-sm font-thin">
                    {t('form.assignSecretToProject.details.type')}
                  </span>
                  <span>
                    {selectedSecret?.type ? (
                      t(`secretType.${selectedSecret.type}`)
                    ) : (
                      <NoDataDisplay />
                    )}
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-sm font-thin">
                    {t('form.assignSecretToProject.details.useCase')}
                  </span>
                  <span>
                    {selectedSecret?.useCase ? (
                      t(`useCase.${selectedSecret.useCase}`)
                    ) : (
                      <NoDataDisplay />
                    )}
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-sm font-thin">
                    {t('form.assignSecretToProject.details.updatedAt')}
                  </span>
                  <span>
                    {selectedSecret?.updatedAt ? (
                      displayTimestamp(new Date(selectedSecret.updatedAt))
                    ) : (
                      <NoDataDisplay />
                    )}
                  </span>
                </div>

                <div className="flex flex-col">
                  <span className="text-sm font-thin">
                    {t('form.assignSecretToProject.details.assignTo')}
                  </span>
                  <SecretProjectAssignedTo secret={selectedSecret} />
                </div>

                <div className="flex flex-col">
                  <span className="text-sm font-thin">
                    {t('form.assignSecretToProject.details.status')}
                  </span>
                  <span className="text-sm">
                    {selectedSecret?.status ? (
                      <SecretStatus
                        status={selectedSecret.status}
                        statusReason={selectedSecret.statusReason}
                        secondaryStatusReason={undefined}
                      />
                    ) : (
                      <NoDataDisplay />
                    )}
                  </span>
                </div>
              </div>
            </section>
          </div>
        );
      }}
      validationSchema={formSchema}
    />
  );
};

export default AssignSecretToProject;
