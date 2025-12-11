// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem, Textarea } from '@heroui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { createProjectSecret, createSecret } from '@/services/app/secrets';

import { APIRequestError } from '@/utils/app/errors';
import { isDuplicateSecret } from '@/utils/app/secrets';

import { SecretScope, SecretType, SecretUseCase } from '@/types/enums/secrets';
import { FormField } from '@/types/forms/forms';
import { Project } from '@/types/projects';
import {
  AddSecretFormData,
  CreateProjectSecretRequest,
  CreateSecretRequest,
  Secret,
} from '@/types/secrets';

import { DrawerForm } from '@/components/shared/Drawer';
import { FormFieldComponent } from '@/components/shared/ManagedForm/FormFieldComponent';

import {
  EXTERNAL_SECRETS_API_GROUP,
  EXTERNAL_SECRETS_KIND,
  KUBERNETES_SECRETS_KIND,
  KUBERNETES_SECRETS_VERSION,
  nameRegex,
} from './constants';

import { parseAllDocuments } from 'yaml';
import { ZodType, z } from 'zod';
import { FormSelect } from '@/components/shared/ManagedForm';

interface Props {
  isOpen: boolean;
  projects: Project[];
  project?: Project;
  secrets: Secret[];
  disabledProjectIds?: string[];
  onClose: () => void;
  restrictToUseCases?: SecretUseCase[];
}

export const AddSecret: React.FC<Props> = ({
  isOpen,
  projects,
  secrets,
  onClose,
  disabledProjectIds = [],
  project,
  restrictToUseCases,
}) => {
  const { t } = useTranslation('secrets');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const manifestYamlValidator = useCallback(
    (
      expectedApiVersion: string | ((apiVersion: string) => boolean),
      expectedKind: string,
    ) => {
      return (value: string) => {
        try {
          const yamls = parseAllDocuments(value);
          if (!Array.isArray(yamls) || yamls.length !== 1) {
            return 'form.add.field.manifest.error.yaml.multiple';
          }
          const yamlDoc = yamls[0];
          const yaml = yamlDoc?.toJSON?.() ?? {};

          // Validate apiVersion
          const isValidApiVersion =
            typeof expectedApiVersion === 'function'
              ? expectedApiVersion(yaml?.apiVersion)
              : yaml?.apiVersion === expectedApiVersion;

          if (!yaml || !yaml.apiVersion || !isValidApiVersion) {
            return typeof expectedApiVersion === 'function'
              ? 'form.add.field.manifest.error.yaml.incorrectGroup'
              : 'form.add.field.manifest.error.yaml.incorrectVersion';
          }

          if (!yaml || yaml.kind !== expectedKind) {
            return 'form.add.field.manifest.error.yaml.incorrectKind';
          }

          if (
            !yaml.metadata ||
            typeof yaml.metadata.name !== 'string' ||
            yaml.metadata.name.length === 0
          ) {
            return 'form.add.field.manifest.error.yaml.noName';
          }

          // Validate Kubernetes resource name
          if (!nameRegex.test(yaml.metadata.name)) {
            return 'form.add.field.manifest.error.yaml.invalidName';
          }

          return true;
        } catch {
          return 'form.add.field.manifest.error.yaml.malformed';
        }
      };
    },
    [],
  );

  const isValidExternalSecret = useMemo(
    () =>
      manifestYamlValidator(
        (apiVersion) => apiVersion?.startsWith(EXTERNAL_SECRETS_API_GROUP),
        EXTERNAL_SECRETS_KIND,
      ),
    [manifestYamlValidator],
  );

  const isValidKubernetesSecret = useMemo(
    () =>
      manifestYamlValidator(
        KUBERNETES_SECRETS_VERSION,
        KUBERNETES_SECRETS_KIND,
      ),
    [manifestYamlValidator],
  );

  const { mutate: addSecret, isPending } = useMutation({
    mutationFn: async (
      data: CreateSecretRequest | CreateProjectSecretRequest,
    ) => {
      if (project) {
        return createProjectSecret(
          project.id,
          data as CreateProjectSecretRequest,
        );
      }
      return createSecret(data as CreateSecretRequest);
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

      const manifest = yamlDoc?.toJSON?.() ?? {};
      const name = manifest.metadata?.name ?? '';

      addSecret({
        type: data.type,
        name,
        use_case: data.context ?? SecretUseCase.GENERIC,
        scope: project ? SecretScope.PROJECT : SecretScope.ORGANIZATION,
        project_ids: project ? [project.id] : data.projectIds,
        manifest: data.manifest,
      });
    },
    [addSecret, project],
  );

  const formSchema = useMemo(
    () =>
      z
        .object({
          projectIds: z.preprocess((val: unknown) => {
            if (Array.isArray(val)) return val;
            if (typeof val === 'string' && val !== '') return val.split(',');
            return [];
          }, z.array(z.string())),
          manifest: z.string().optional(),
          type: z.custom<SecretType>(),
          context: z.custom<SecretUseCase>(),
          name: z.string().optional(),
          token: z.string().optional(),
        })
        .superRefine((data, ctx) => {
          // Validate name and token for Kubernetes secrets with HuggingFace context

          const resourceKey =
            data.type === SecretType.EXTERNAL_SECRET
              ? 'form.add.field.manifest.externalSecret.name'
              : 'form.add.field.manifest.secret.name';

          // Validate manifest for other cases
          if (!data.manifest || data.manifest.length < 2) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('form.add.field.manifest.error.required', {
                resource: t(resourceKey),
              }),
              path: ['manifest'],
            });
            return;
          }

          const isValid =
            data.type === SecretType.EXTERNAL_SECRET
              ? isValidExternalSecret(data.manifest)
              : isValidKubernetesSecret(data.manifest);

          if (isValid !== true) {
            const message =
              typeof isValid === 'string'
                ? t(isValid, { resource: t(resourceKey) })
                : t('form.add.field.manifest.error.yaml.malformed', {
                    resource: t(resourceKey),
                  });

            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message,
              path: ['manifest'],
            });
            return;
          }

          // Check for duplicate name+type combination based on scope
          const yamls = parseAllDocuments(data.manifest || '');
          const yamlDoc = yamls[0];
          const manifest = yamlDoc?.toJSON?.() ?? {};
          const secretName = manifest.metadata?.name ?? '';

          if (isDuplicateSecret(secrets, secretName, data.type, project)) {
            const secretTypeLabel = t(`secretType.${data.type}`);
            const scopeLabel = project ? 'project' : 'organization';

            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('form.add.field.manifest.error.yaml.duplicateName', {
                resource: t(resourceKey),
                secretType: secretTypeLabel,
                name: secretName,
                scope: scopeLabel,
              }),
              path: ['manifest'],
            });
          }
        }) as ZodType<AddSecretFormData>,
    [t, isValidExternalSecret, isValidKubernetesSecret, project, secrets],
  );

  const formTypeContent: FormField<AddSecretFormData>[] = useMemo(
    () => [
      {
        name: 'type',
        label: t('form.add.field.type.label'),
        placeholder: t('form.add.field.type.placeholder'),
        isRequired: true,
        component: (formElemProps) => (
          <FormSelect
            defaultSelectedKeys={[SecretType.EXTERNAL_SECRET]}
            labelPlacement="outside"
            variant="bordered"
            {...formElemProps}
          >
            {project ? (
              Object.values(SecretType).map((type) => (
                <SelectItem key={type}>{t(`secretType.${type}`)}</SelectItem>
              ))
            ) : (
              <SelectItem key={SecretType.EXTERNAL_SECRET}>
                {t(`secretType.${SecretType.EXTERNAL_SECRET}`)}
              </SelectItem>
            )}
          </FormSelect>
        ),
      },
      {
        name: 'context',
        label: t('form.add.field.context.label'),
        placeholder: t('form.add.field.context.placeholder'),
        isRequired: true,
        component: (formElemProps) => (
          <FormSelect
            labelPlacement="outside"
            defaultSelectedKeys={
              restrictToUseCases && restrictToUseCases.length > 0
                ? [restrictToUseCases[0]]
                : [SecretUseCase.GENERIC]
            }
            variant="bordered"
            {...formElemProps}
            disabledKeys={project ? [SecretUseCase.S3] : []}
            isDisabled={restrictToUseCases && restrictToUseCases.length === 1}
          >
            {restrictToUseCases && restrictToUseCases.length > 0
              ? restrictToUseCases.map((useCase) => (
                  <SelectItem key={useCase}>
                    {t(`useCase.${useCase}`)}
                  </SelectItem>
                ))
              : Object.values(SecretUseCase).map((type) => (
                  <SelectItem key={type}>{t(`useCase.${type}`)}</SelectItem>
                ))}
          </FormSelect>
        ),
      },
    ],
    [t, project, restrictToUseCases],
  );

  const externalSecretManifestField: FormField<AddSecretFormData> = useMemo(
    () => ({
      name: 'manifest',
      label: t('form.add.field.manifest.externalSecret.label'),
      placeholder: t('form.add.field.manifest.externalSecret.placeholder'),
      description: t('form.add.field.manifest.externalSecret.description'),
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
    }),
    [t],
  );

  const secretManifestField: FormField<AddSecretFormData> = useMemo(
    () => ({
      name: 'manifest',
      label: t('form.add.field.manifest.secret.label'),
      placeholder: t('form.add.field.manifest.secret.placeholder'),
      description: t('form.add.field.manifest.secret.description'),
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
    }),
    [t],
  );

  const formProjectContent: FormField<AddSecretFormData>[] = useMemo(
    () => [
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
    ],
    [t, project, projects, disabledProjectIds],
  );

  return (
    <DrawerForm<AddSecretFormData>
      isOpen={isOpen}
      isActioning={isPending}
      onFormSuccess={(values) => {
        handleAddSecretSubmit(values);
        onClose();
      }}
      defaultValues={{
        type: SecretType.EXTERNAL_SECRET,
        context:
          restrictToUseCases && restrictToUseCases.length > 0
            ? restrictToUseCases[0]
            : SecretUseCase.GENERIC,
      }}
      onCancel={onClose}
      title={t(`form.add.title.${project ? 'project' : 'general'}`)}
      confirmText={t('form.add.action.add')}
      cancelText={t('form.add.action.cancel')}
      renderFields={(form) => {
        const watchType = form.watch('type');

        const manifestField =
          watchType === SecretType.EXTERNAL_SECRET
            ? externalSecretManifestField
            : secretManifestField;
        const formContent = [
          ...formTypeContent,
          manifestField,
          ...formProjectContent,
        ];
        return (
          <div className="flex flex-col gap-4">
            {formContent.map((field) => (
              <FormFieldComponent<AddSecretFormData>
                key={field.name}
                formField={field}
                errorMessage={form.formState.errors[field.name]?.message}
                register={form.register}
                form={form}
              />
            ))}
          </div>
        );
      }}
      validationSchema={formSchema}
    />
  );
};

export default AddSecret;
