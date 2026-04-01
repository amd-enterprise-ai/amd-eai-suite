// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem, Textarea } from '@heroui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { createProjectSecret, createSecret } from '@/services/app';

import { APIRequestError } from '@amdenterpriseai/utils/app';
import { isDuplicateSecret } from '@amdenterpriseai/utils/app';

import { SecretScope, SecretType, SecretUseCase } from '@amdenterpriseai/types';
import { FormField } from '@amdenterpriseai/types';
import { Project } from '@amdenterpriseai/types';
import {
  AddSecretFormData,
  CreateProjectSecretRequest,
  CreateSecretRequest,
  Secret,
} from '@amdenterpriseai/types';

import { DrawerForm } from '@amdenterpriseai/components';
import { FormFieldComponent } from '@amdenterpriseai/components';

import {
  EXTERNAL_SECRETS_API_GROUP,
  EXTERNAL_SECRETS_KIND,
  KUBERNETES_SECRETS_KIND,
  KUBERNETES_SECRETS_VERSION,
  nameRegex,
} from './constants';

import { parseAllDocuments } from 'yaml';
import { ZodType, z } from 'zod';
import { FormSelect } from '@amdenterpriseai/components';

interface Props {
  isOpen: boolean;
  projects: Project[];
  secrets: Secret[];
  defaultScope: SecretScope;
  scopeSelectDisabled: boolean;
  projectSelectDisabled: boolean;
  disabledProjectIds?: string[];
  onCreateSuccess: () => void;
  onClose: () => void;
  restrictToUseCases?: SecretUseCase[];
}

export const AddSecret: React.FC<Props> = ({
  isOpen,
  defaultScope,
  scopeSelectDisabled,
  projectSelectDisabled,
  projects,
  secrets,
  onCreateSuccess,
  onClose,
  disabledProjectIds = [],
  restrictToUseCases,
}) => {
  const { t } = useTranslation('secrets');
  const { toast } = useSystemToast();

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
    mutationFn: async (data: CreateSecretRequest) => {
      if (data.scope === SecretScope.PROJECT) {
        return createProjectSecret(
          data.project_ids[0],
          data as CreateProjectSecretRequest,
        );
      }
      return createSecret(data as CreateSecretRequest);
    },
    onSuccess: () => {
      onCreateSuccess();
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
        use_case: data.useCase ?? SecretUseCase.GENERIC,
        scope: data.scope,
        project_ids: data.projectIds,
        manifest: data.manifest,
      });
    },
    [addSecret],
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
          scope: z.nativeEnum(SecretScope),
          type: z.nativeEnum(SecretType),
          useCase: z.nativeEnum(SecretUseCase),
          name: z.string().optional(),
          token: z.string().optional(),
        })
        .refine(
          (data) =>
            data.scope !== SecretScope.PROJECT || data.projectIds.length > 0,
          {
            message: t('form.add.field.projectIds.error.required'),
            path: ['projectIds'],
          },
        )
        .refine(
          (data) =>
            data.scope !== SecretScope.PROJECT ||
            data.useCase !== SecretUseCase.S3,
          {
            message: t('form.add.field.useCase.error.s3NotAllowedForProject'),
            path: ['useCase'],
          },
        )
        .superRefine((data, ctx) => {
          const resourceKey =
            data.type === SecretType.EXTERNAL_SECRET
              ? 'form.add.field.manifest.externalSecret.name'
              : 'form.add.field.manifest.secret.name';

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
            const expectedKind =
              data.type === SecretType.EXTERNAL_SECRET
                ? EXTERNAL_SECRETS_KIND
                : KUBERNETES_SECRETS_KIND;

            const message =
              typeof isValid === 'string'
                ? t(isValid, { resource: t(resourceKey), kind: expectedKind })
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

          const yamls = parseAllDocuments(data.manifest || '');
          const yamlDoc = yamls[0];
          const manifest = yamlDoc?.toJSON?.() ?? {};
          const secretName = manifest.metadata?.name ?? '';

          if (
            isDuplicateSecret(
              secrets,
              secretName,
              data.type,
              data.scope,
              data.scope === SecretScope.PROJECT && data.projectIds?.[0]
                ? data.projectIds[0]
                : undefined,
            )
          ) {
            const secretTypeLabel = t(`secretType.${data.type}`);
            const scopeLabel = data.scope;

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
    [t, isValidExternalSecret, isValidKubernetesSecret, secrets],
  );

  const formScopeContent: FormField<AddSecretFormData> = useMemo(
    () => ({
      name: 'scope',
      label: t('form.add.field.scope.label'),
      placeholder: t('form.add.field.scope.placeholder'),
      isRequired: true,
      component: (formElemProps) => (
        <FormSelect
          defaultSelectedKeys={[defaultScope]}
          {...formElemProps}
          isDisabled={scopeSelectDisabled}
        >
          <SelectItem key={SecretScope.ORGANIZATION}>
            {t(`secretScope.Organization`)}
          </SelectItem>
          <SelectItem key={SecretScope.PROJECT}>
            {t(`secretScope.Project`)}
          </SelectItem>
        </FormSelect>
      ),
    }),
    [t, defaultScope, scopeSelectDisabled],
  );

  const getFormTypeContent = useCallback(
    (scope: SecretScope): FormField<AddSecretFormData> => {
      return {
        name: 'type',
        label: t('form.add.field.type.label'),
        placeholder: t('form.add.field.type.placeholder'),
        isRequired: true,
        component: (formElemProps) => (
          <FormSelect
            defaultSelectedKeys={[SecretType.EXTERNAL_SECRET]}
            {...formElemProps}
          >
            {scope === SecretScope.PROJECT ? (
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
      };
    },
    [t],
  );

  const getFormUseCaseContent = useCallback(
    (scope: SecretScope): FormField<AddSecretFormData> => {
      return {
        name: 'useCase',
        label: t('form.add.field.useCase.label'),
        placeholder: t('form.add.field.useCase.placeholder'),
        isRequired: true,
        component: (formElemProps) => (
          <FormSelect
            defaultSelectedKeys={
              restrictToUseCases && restrictToUseCases.length > 0
                ? [restrictToUseCases[0]]
                : [SecretUseCase.GENERIC]
            }
            {...formElemProps}
            disabledKeys={
              scope === SecretScope.PROJECT ? [SecretUseCase.S3] : []
            }
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
      };
    },
    [t, restrictToUseCases],
  );

  const getFormProjectContent = useCallback(
    (scope: SecretScope): FormField<AddSecretFormData> => {
      return {
        name: 'projectIds',
        label: t('form.add.field.projectIds.label'),
        placeholder: t('form.add.field.projectIds.placeholder'),
        description: t('form.add.field.projectIds.description'),
        isRequired: scope === SecretScope.PROJECT,
        component: (formElemProps) => (
          <FormSelect
            selectionMode={
              scope === SecretScope.PROJECT ? 'single' : 'multiple'
            }
            disallowEmptySelection={scope === SecretScope.PROJECT}
            classNames={{ label: 'pb-2' }}
            defaultSelectedKeys={
              scope === SecretScope.PROJECT && projects.length >= 1
                ? [projects[0].id]
                : []
            }
            {...formElemProps}
            disabledKeys={disabledProjectIds}
            isDisabled={projectSelectDisabled}
          >
            {projects.map((proj) => (
              <SelectItem key={proj.id}>{proj.name}</SelectItem>
            ))}
          </FormSelect>
        ),
      };
    },
    [t, disabledProjectIds, projects, projectSelectDisabled],
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

  return (
    <DrawerForm<AddSecretFormData>
      isOpen={isOpen}
      isActioning={isPending}
      onFormSuccess={(values) => {
        handleAddSecretSubmit(values);
        onClose();
      }}
      defaultValues={{
        scope: defaultScope,
        type: SecretType.EXTERNAL_SECRET,
        useCase:
          restrictToUseCases && restrictToUseCases.length > 0
            ? restrictToUseCases[0]
            : SecretUseCase.GENERIC,
        projectIds: projects.length === 1 ? [projects[0].id] : [],
      }}
      onCancel={onClose}
      title={t('form.add.title')}
      confirmText={t('form.add.action.add')}
      cancelText={t('form.add.action.cancel')}
      renderFields={(form) => {
        const watchType = form.watch('type');
        const watchScope = form.watch('scope');

        const manifestField =
          watchType === SecretType.EXTERNAL_SECRET
            ? externalSecretManifestField
            : secretManifestField;

        const formContent = [
          formScopeContent,
          getFormTypeContent(watchScope),
          getFormUseCaseContent(watchScope),
          manifestField,
          getFormProjectContent(watchScope),
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
