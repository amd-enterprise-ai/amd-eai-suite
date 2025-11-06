// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { editCluster as editClusterAPI } from '@/services/app/clusters';

import { APIRequestError } from '@/utils/app/errors';

import {
  Cluster,
  EditClusterFormData,
  EditClusterRequest,
} from '@/types/clusters';
import { FormField } from '@/types/forms/forms';

import { DrawerForm } from '@/components/shared/DrawerForm';
import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';

import { ZodType, z } from 'zod';

interface Props {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  cluster: Cluster;
}

export const EditCluster: React.FC<Props> = ({
  isOpen,
  onOpenChange,
  cluster,
}) => {
  const { t } = useTranslation('clusters');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const { mutate: editCluster, isPending } = useMutation({
    mutationFn: async (data: EditClusterRequest) =>
      editClusterAPI(cluster.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['clusters'],
      });
      toast.success(t('form.edit.notification.success'));
    },
    onError: (error) => {
      toast.error(t('form.edit.notification.error'), error as APIRequestError);
    },
  });

  const handleEditClusterSubmit = useCallback(
    async (data: EditClusterFormData): Promise<void> => {
      editCluster({
        base_url: data.baseUrl,
      });
    },
    [editCluster],
  );

  const formSchema = useMemo(
    () =>
      z.object({
        baseUrl: z
          .string()
          .refine(
            (val) =>
              val === '' || /^(https?:\/\/)[^\s/$.?#].[^\s]*$/i.test(val),
            {
              message: t('form.edit.field.baseUrl.error.invalid'),
            },
          ),
      }) as ZodType<EditClusterFormData>,
    [t],
  );

  const formContent: FormField<EditClusterFormData>[] = [
    {
      name: 'baseUrl',
      label: t('form.edit.field.baseUrl.label'),
      placeholder: t('form.edit.field.baseUrl.placeholder'),
      isRequired: true,
    },
  ];

  return (
    <DrawerForm<EditClusterFormData>
      isOpen={isOpen}
      isActioning={isPending}
      onFormSuccess={(values) => {
        handleEditClusterSubmit({
          baseUrl: values.baseUrl,
        });
        onOpenChange(false);
      }}
      onCancel={() => onOpenChange(false)}
      title={t('form.edit.title')}
      confirmText={t('form.edit.action.save')}
      cancelText={t('form.edit.action.cancel')}
      renderFields={(form) => (
        <div className="flex flex-col gap-4">
          {formContent.map((field) => (
            <FormFieldComponent<EditClusterFormData>
              key={field.name}
              formField={field}
              errorMessage={form.formState.errors[field.name]?.message}
              register={form.register}
              defaultValue={cluster.baseUrl}
            />
          ))}
        </div>
      )}
      validationSchema={formSchema}
    />
  );
};

export default EditCluster;
