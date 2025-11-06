// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem, Textarea } from '@heroui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { createSecret } from '@/services/app/secrets';

import { APIRequestError } from '@/utils/app/errors';

import { SecretScope, SecretType } from '@/types/enums/secrets';
import { FormField } from '@/types/forms/forms';
import { Project } from '@/types/projects';
import {
  AddSecretFormData,
  CreateSecretRequest,
  Secret,
} from '@/types/secrets';

import { DrawerForm } from '@/components/shared/DrawerForm';
import { FormFieldComponent } from '@/components/shared/ManagedForm/FormFieldComponent';

import { EXTERNAL_SECRETS_API_GROUP } from './constants';

import { parseAllDocuments } from 'yaml';
import { ZodType, z } from 'zod';

interface Props {
  isOpen: boolean;
  projects: Project[];
  project?: Project;
  secrets: Secret[];
  disabledProjectIds?: string[];
  onClose: () => void;
}

export const AddSecret: React.FC<Props> = ({
  isOpen,
  projects,
  secrets,
  onClose,
  disabledProjectIds = [],
  project,
}) => {
  const { t } = useTranslation('secrets');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const isValidExternalSecret = useMemo(() => {
    return (value: string) => {
      try {
        const yamls = parseAllDocuments(value);
        if (!Array.isArray(yamls) || yamls.length !== 1) {
          return 'form.add.field.manifest.error.yaml.multiple';
        }
        const yamlDoc = yamls[0];
        const yaml = yamlDoc?.toJSON?.() ?? {};

        if (
          !yaml ||
          !yaml.apiVersion ||
          !yaml.apiVersion.startsWith(EXTERNAL_SECRETS_API_GROUP)
        ) {
          return 'form.add.field.manifest.error.yaml.incorrectGroup';
        }

        if (!yaml || yaml.kind !== 'ExternalSecret') {
          return 'form.add.field.manifest.error.yaml.notExternalSecret';
        }

        if (
          !yaml.metadata ||
          typeof yaml.metadata.name !== 'string' ||
          yaml.metadata.name.length === 0
        ) {
          return 'form.add.field.manifest.error.yaml.noName';
        }

        // Validate Kubernetes resource name
        const nameRegex = /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/;
        if (!nameRegex.test(yaml.metadata.name)) {
          return 'form.add.field.manifest.error.yaml.invalidName';
        }
        if (!yaml.spec || Object.keys(yaml.spec).length === 0) {
          return 'form.add.field.manifest.error.yaml.noSpec';
        }
        if (secrets.some((secret) => secret.name === yaml.metadata.name)) {
          return 'form.add.field.manifest.error.yaml.duplicateName';
        }
        return true;
      } catch {
        return 'form.add.field.manifest.error.yaml.malformed';
      }
    };
  }, [secrets]);

  const { mutate: addSecret, isPending } = useMutation({
    mutationFn: async (data: CreateSecretRequest) => {
      return createSecret(data);
    },
    onSuccess: () => {
      if (project) {
        queryClient.invalidateQueries({
          queryKey: ['project-secrets', project.id],
        });
      }
      queryClient.invalidateQueries({
        queryKey: ['secrets'],
      });
      toast.success(t('form.add.notification.success'));
    },
    onError: (error) => {
      toast.error(t('form.add.notification.error'), error as APIRequestError);
    },
  });

  const handleAddSecretSubmit = useCallback(
    async (data: AddSecretFormData): Promise<void> => {
      const yamls = parseAllDocuments(data.manifest);
      const yamlDoc = yamls[0];
      const yaml = yamlDoc?.toJSON?.() ?? {};
      const name = yaml.metadata?.name || '';
      addSecret({
        type: data.type,
        name: name,
        scope: SecretScope.ORGANIZATION,
        project_ids: project ? [project.id] : data.projectIds,
        manifest: data.manifest,
      });
    },
    [addSecret, project],
  );

  const formSchema = useMemo(
    () =>
      z.object({
        projectIds: z.preprocess((val: unknown) => {
          if (Array.isArray(val)) return val;
          if (typeof val === 'string' && val !== '') return val.split(',');
          return [];
        }, z.array(z.string())),
        manifest: z
          .string()
          .min(2, t('form.add.field.manifest.error.required'))
          .refine(
            (value) => isValidExternalSecret(value) === true,
            (value) => {
              const result = isValidExternalSecret(value);
              if (result === true) {
                return {
                  message: t('form.add.field.manifest.error.yaml.malformed'),
                }; // fallback, should not happen
              }
              if (typeof result === 'string') {
                return { message: t(result) };
              }
              return {
                message: t('form.add.field.manifest.error.yaml.malformed'),
              };
            },
          ),
        type: z.custom<SecretType>(),
      }) as ZodType<AddSecretFormData>,
    [t, isValidExternalSecret],
  );

  const formContent: FormField<AddSecretFormData>[] = [
    {
      name: 'type',
      label: t('form.add.field.type.label'),
      placeholder: t('form.add.field.type.placeholder'),
      isRequired: true,
      component: (formElemProps) => (
        <Select labelPlacement="outside" variant="bordered" {...formElemProps}>
          <SelectItem key={SecretType.EXTERNAL}>
            {t(`secretType.${SecretType.EXTERNAL}`)}
          </SelectItem>
        </Select>
      ),
    },
    {
      name: 'manifest',
      label: t('form.add.field.manifest.label'),
      placeholder: t('form.add.field.manifest.placeholder'),
      description: t('form.add.field.manifest.description'),
      isRequired: true,
      component: (formElemProps) => (
        <Textarea
          labelPlacement="outside"
          minRows={15}
          maxRows={30}
          variant="bordered"
          {...formElemProps}
          onChange={(event) => {
            formElemProps.onChange({
              target: {
                value: event.target.value,
                name: formElemProps.name,
              },
            });
          }}
          onBlur={(event) => {
            formElemProps.onBlur({
              target: {
                value: event.target.value,
                name: formElemProps.name,
              },
            });
          }}
        />
      ),
    },
    {
      name: 'projectIds',
      label: t('form.add.field.projectIds.label'),
      placeholder: t('form.add.field.projectIds.placeholder'),
      description: t('form.add.field.projectIds.description'),
      isRequired: false,
      component: (formElemProps) => (
        <Select
          labelPlacement="outside"
          selectionMode="multiple"
          classNames={{ label: 'pb-2' }}
          defaultSelectedKeys={project ? [project.id] : []}
          variant="bordered"
          {...formElemProps}
          disabledKeys={disabledProjectIds}
          isDisabled={!!project}
        >
          {(project ? [project] : projects).map((proj) => (
            <SelectItem key={proj.id}>{proj.name}</SelectItem>
          ))}
        </Select>
      ),
    },
  ];

  return (
    <DrawerForm<AddSecretFormData>
      isOpen={isOpen}
      isActioning={isPending}
      onFormSuccess={(values) => {
        handleAddSecretSubmit({
          projectIds: values.projectIds,
          type: values.type,
          manifest: values.manifest,
        });
        onClose();
      }}
      onCancel={onClose}
      title={t('form.add.title')}
      confirmText={t('form.add.action.add')}
      cancelText={t('form.add.action.cancel')}
      renderFields={(form) => (
        <div className="flex flex-col gap-4">
          {formContent.map((field) => (
            <FormFieldComponent<AddSecretFormData>
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

export default AddSecret;
