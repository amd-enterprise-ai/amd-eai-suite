// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { IconArrowLeft } from '@tabler/icons-react';
import { useRouter } from 'next/router';
import { useTranslation } from 'next-i18next';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useForm, type Resolver } from 'react-hook-form';
import { z } from 'zod';

import { ActionButton, StepPage } from '@amdenterpriseai/components';
import { PageLoader } from '@/components/shared/PageLoader';
import { useSystemToast } from '@amdenterpriseai/hooks';
import { APIRequestError } from '@amdenterpriseai/utils/app';
import type { StepPageHandle, StepPageStep } from '@amdenterpriseai/types';

import { useProject } from '@/contexts/ProjectContext';
import { useRuntimeProfileCatalog } from '@/hooks/useRuntimeProfileCatalog';
import {
  collectExistingDisplayNames,
  extractCustomModelCanonicalName,
  extractCustomModelDisplayMetadata,
  getCustomModel,
  listCustomModels,
  patchCustomModel,
} from '@/lib/app/custom-models';
import { onboardModel, previewModelSource } from '@/lib/app/model-import';
import {
  formValuesToProfileOverrides,
  formValuesToProfilePatch,
  isRuntimeYamlMappingValid,
  profileOverridesToFormValues,
  profileOverridesToOnboardBody,
} from '@/lib/app/runtimeProfileMappers';
import type { CustomModelPatchBody } from '@/types/custom-models';
import type { ModelSourcePreviewResponse } from '@/types/model-import';

import StepModelInformation from './steps/StepModelInformation';
import StepModelSource from './steps/StepModelSource';
import StepRuntimeProfile from './steps/StepRuntimeProfile';
import {
  DEFAULT_CUSTOM_MODEL_IMPORT_VALUES,
  type CustomModelImportFormValues,
} from './types';

const splitTags = (raw: string): string[] =>
  raw
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);

const RUNTIME_FIELD_NAMES = [
  'containerImage',
  'containerVersion',
  'acceleratorType',
  'accelerator',
  'acceleratorCount',
  'modelPrecision',
] as const satisfies readonly (keyof CustomModelImportFormValues)[];

type CustomModelImportPageProps = {
  /** `create` runs the import flow; `edit` prefills from an existing model. */
  mode?: 'create' | 'edit';
  /** AIMModel CR name; required (and only used) in edit mode. */
  modelId?: string;
};

/**
 * Three-step wizard for importing or editing a custom model in a project.
 *
 * Create mode owns the cross-step form state, gates step transitions on backend
 * validation (preview before step 2, onboard on submit), and routes back to the
 * custom-models tab on success or cancel.
 *
 * Edit mode prefills the form from the live model, renders step 1 (source)
 * read-only and skips the preview call, and saves only the changed fields via a
 * single PATCH. Runtime-profile edits require a derived AIMProfile, so step 3 is
 * disabled until the model finishes importing.
 */
export const CustomModelImportPage = ({
  mode = 'create',
  modelId,
}: CustomModelImportPageProps) => {
  const { t } = useTranslation('models', {
    keyPrefix: 'customModels.import',
  });
  const { t: tActions } = useTranslation('common', { keyPrefix: 'actions' });
  const router = useRouter();
  const { toast } = useSystemToast();
  const { activeProject, projectPath } = useProject();
  const queryClient = useQueryClient();
  const projectSlugFromRoute = useMemo(() => {
    const raw = router.query.project;
    if (typeof raw === 'string') {
      return raw;
    }
    if (Array.isArray(raw) && raw.length > 0 && typeof raw[0] === 'string') {
      return raw[0];
    }
    return '';
  }, [router.query.project]);
  /** Prefer resolved project from context; fall back to `[project]` URL segment so edit-mode fetch is not blocked forever when context lags or the slug is not in the loaded list. */
  const namespace = activeProject || projectSlugFromRoute;
  const catalog = useRuntimeProfileCatalog(namespace);
  const isEdit = mode === 'edit';

  const stepperRef = useRef<StepPageHandle>(null);
  const [preview, setPreview] = useState<
    ModelSourcePreviewResponse | undefined
  >(undefined);
  const [prefilled, setPrefilled] = useState(false);

  const modelQuery = useQuery({
    queryKey: ['project', namespace, 'custom-model', modelId],
    queryFn: () => getCustomModel(namespace, modelId ?? ''),
    enabled: isEdit && Boolean(namespace) && Boolean(modelId),
  });
  const model = modelQuery.data;
  // Runtime edits merge-patch the live AIMProfile, which only exists once the
  // model is past import; gate step 3 on its presence to avoid a 409.
  const profileReady = Boolean(model?.phase?.templateReady);
  const runtimeEditBlocked = isEdit && !profileReady;

  // Existing custom models in the project, used to warn (not block) when the
  // chosen display name would overwrite another model's settings. Reuses the
  // Custom Models tab's cache key; the warning is advisory, so a slightly stale
  // list is acceptable — fetch only when the cache is empty and skip refetch on
  // remount/focus rather than re-listing on every wizard entry.
  const customModelsQuery = useQuery({
    queryKey: ['project', namespace, 'custom-models'],
    queryFn: () => listCustomModels(namespace),
    enabled: Boolean(namespace),
    staleTime: 30_000,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
  });
  const existingDisplayNames = useMemo(
    () => collectExistingDisplayNames(customModelsQuery.data ?? [], modelId),
    [customModelsQuery.data, modelId],
  );

  const schema = useMemo(
    () =>
      z
        .object({
          source: z
            .string()
            .trim()
            .min(1, { message: t('errors.sourceRequired') }),
          hfTokenSecretName: z.string().optional().default(''),
          // Display name is a free-form, human-readable label (stored as an
          // annotation), not a K8s resource name — the backend derives the CR
          // name from the repo id. Only non-emptiness is required, matching the
          // backend contract and the comparable fine-tuning model name field.
          displayName: z
            .string()
            .trim()
            .min(1, { message: t('errors.displayNameRequired') }),
          description: z.string().optional().default(''),
          tagsInput: z.string().optional().default(''),
          containerImage: z
            .string()
            .trim()
            .min(1, { message: t('errors.containerImageRequired') }),
          containerVersion: z.string().optional().default(''),
          acceleratorType: z
            .string()
            .trim()
            .min(1, { message: t('errors.acceleratorTypeRequired') }),
          accelerator: z
            .string()
            .trim()
            .min(1, { message: t('errors.acceleratorRequired') }),
          acceleratorCount: z.coerce
            .number()
            .int()
            .min(1, { message: t('errors.acceleratorCountRequired') }),
          modelPrecision: z
            .string()
            .trim()
            .min(1, { message: t('errors.modelPrecisionRequired') }),
          engineArgsYaml: z.string().optional().default(''),
          envVarsYaml: z.string().optional().default(''),
        })
        .superRefine((data, ctx) => {
          const family = catalog.imageFamilies.find(
            (entry) => entry.familyId === data.containerImage,
          );
          const hasTagOptions = (family?.tags.length ?? 0) > 0;
          if (hasTagOptions && !data.containerVersion.trim()) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('errors.containerVersionRequired'),
              path: ['containerVersion'],
            });
          }
          if (!isRuntimeYamlMappingValid(data.engineArgsYaml)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('errors.invalidEngineArgsYaml'),
              path: ['engineArgsYaml'],
            });
          }
          if (!isRuntimeYamlMappingValid(data.envVarsYaml)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('errors.invalidEnvVarsYaml'),
              path: ['envVarsYaml'],
            });
          }
        }),
    [catalog.imageFamilies, t],
  );

  const form = useForm<CustomModelImportFormValues>({
    defaultValues: DEFAULT_CUSTOM_MODEL_IMPORT_VALUES,
    mode: 'onBlur',
    resolver: zodResolver(
      schema,
    ) as unknown as Resolver<CustomModelImportFormValues>,
  });

  const returnToList = useCallback(() => {
    router.push(projectPath('/models/custom-models'));
  }, [router, projectPath]);

  // Prefill once the model and catalog have both settled. We wait for the
  // catalog (not just a successful load) so the reverse mapper can resolve the
  // saved image ref to a family/tag; if the catalog failed, runtime values fall
  // back to defaults and step 3 surfaces the catalog error instead.
  useEffect(() => {
    if (!isEdit || prefilled || !model || catalog.isLoading) {
      return;
    }
    const displayMetadata = extractCustomModelDisplayMetadata(model);
    const runtimeValues = profileOverridesToFormValues(
      model.spec.profiles?.overrides,
      catalog.imageFamilies,
      catalog.accelerators,
    );
    form.reset({
      source: extractCustomModelCanonicalName(model),
      hfTokenSecretName: '',
      displayName: displayMetadata.displayName,
      description: displayMetadata.description,
      tagsInput: displayMetadata.tags.join(', '),
      ...runtimeValues,
    });
    setPrefilled(true);
  }, [
    isEdit,
    prefilled,
    model,
    catalog.isLoading,
    catalog.imageFamilies,
    catalog.accelerators,
    form,
  ]);

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!namespace) {
        throw new APIRequestError(t('errors.noProject'), 422);
      }
      const { source, hfTokenSecretName } = form.getValues();
      return previewModelSource(namespace, {
        source: source.trim(),
        hfTokenSecretName: hfTokenSecretName?.trim() || undefined,
      });
    },
    onSuccess: (result) => {
      setPreview(result);
      form.setValue('displayName', result.displayName ?? '', {
        shouldDirty: false,
      });
      form.setValue('description', result.description ?? '', {
        shouldDirty: false,
      });
      form.setValue('tagsInput', (result.tags ?? []).join(', '), {
        shouldDirty: false,
      });
      stepperRef.current?.setStep(1);
    },
    onError: (error: unknown) => {
      const message =
        error instanceof APIRequestError
          ? error.message
          : t('errors.previewGeneric');
      toast.error(message);
    },
  });

  const onboardMutation = useMutation({
    mutationFn: async (values: CustomModelImportFormValues) => {
      if (!namespace) {
        throw new APIRequestError(t('errors.noProject'), 422);
      }
      if (!preview) {
        throw new APIRequestError(t('errors.missingPreview'), 422);
      }
      if (!preview.sha?.trim()) {
        throw new APIRequestError(t('errors.missingPreview'), 422);
      }
      const description = values.description.trim();
      const hfTokenSecretName = values.hfTokenSecretName?.trim();
      const overrides = formValuesToProfileOverrides(
        values,
        catalog.imageFamilies,
      );
      const body = profileOverridesToOnboardBody(
        overrides,
        {
          repoId: preview.repoId,
          revision: preview.revision,
          sha: preview.sha,
          displayName: values.displayName.trim(),
          tags: splitTags(values.tagsInput),
          ...(description ? { description } : {}),
          ...(hfTokenSecretName ? { hfTokenSecretName } : {}),
        },
        catalog.imageFamilies,
        catalog.accelerators,
      );
      return onboardModel(namespace, body);
    },
    onSuccess: () => {
      toast.success(t('notifications.onboardSuccess'));
      returnToList();
    },
    onError: (error: unknown) => {
      const message =
        error instanceof APIRequestError
          ? error.message
          : t('errors.onboardGeneric');
      toast.error(message);
    },
  });

  const patchMutation = useMutation({
    mutationFn: async (values: CustomModelImportFormValues) => {
      if (!namespace || !modelId) {
        throw new APIRequestError(t('errors.noProject'), 422);
      }
      const dirty = form.formState.dirtyFields;
      const body: CustomModelPatchBody = {};
      if (dirty.displayName) {
        body.displayName = values.displayName.trim();
      }
      if (dirty.description) {
        body.description = values.description.trim();
      }
      if (dirty.tagsInput) {
        body.tags = splitTags(values.tagsInput);
      }

      const runtimeDirty =
        RUNTIME_FIELD_NAMES.some((field) => dirty[field]) ||
        Boolean(dirty.engineArgsYaml || dirty.envVarsYaml);
      if (runtimeDirty) {
        if (!profileReady) {
          throw new APIRequestError(t('errors.profileNotReady'), 409);
        }
        const { image, customProfile } = formValuesToProfilePatch(
          values,
          catalog.imageFamilies,
          catalog.accelerators,
        );
        body.image = image;
        body.customProfile = customProfile;
      }

      if (Object.keys(body).length === 0) {
        return { changed: false };
      }
      await patchCustomModel(namespace, modelId, body);
      return { changed: true };
    },
    onSuccess: (result) => {
      if (result.changed) {
        toast.success(t('notifications.editSuccess'));
        queryClient.invalidateQueries({
          queryKey: ['project', namespace, 'custom-models'],
        });
        queryClient.invalidateQueries({
          queryKey: ['project', namespace, 'custom-model', modelId],
        });
      }
      returnToList();
    },
    onError: (error: unknown) => {
      const message =
        error instanceof APIRequestError
          ? error.message
          : t('errors.editGeneric');
      toast.error(message);
    },
  });

  const goToStep = useCallback((step: number) => {
    stepperRef.current?.setStep(step);
  }, []);

  const advanceFromSource = useCallback(async () => {
    if (isEdit) {
      goToStep(1);
      return;
    }
    const valid = await form.trigger(['source']);
    if (!valid) return;
    previewMutation.mutate();
  }, [form, goToStep, isEdit, previewMutation]);

  const advanceFromInformation = useCallback(async () => {
    const valid = await form.trigger(['displayName']);
    if (!valid) return;
    goToStep(2);
  }, [form, goToStep]);

  const submitFromRuntime = useCallback(async () => {
    if (
      catalog.isLoading ||
      catalog.isError ||
      catalog.accelerators.length === 0
    ) {
      return;
    }
    const valid = await form.trigger([
      ...RUNTIME_FIELD_NAMES,
      'engineArgsYaml',
      'envVarsYaml',
    ]);
    if (!valid) return;
    onboardMutation.mutate(form.getValues());
  }, [
    catalog.accelerators.length,
    catalog.isError,
    catalog.isLoading,
    form,
    onboardMutation,
  ]);

  const saveFromEdit = useCallback(async () => {
    if (catalog.isLoading) return;
    const dirty = form.formState.dirtyFields;
    const runtimeDirty =
      RUNTIME_FIELD_NAMES.some((field) => dirty[field]) ||
      Boolean(dirty.engineArgsYaml || dirty.envVarsYaml);
    // Display name is always required. Runtime fields are validated only when
    // the user changed them (same scope as the PATCH body) so a metadata-only
    // save is not blocked by an incomplete catalog (e.g. empty accelerators).
    const fieldsToValidate: (keyof CustomModelImportFormValues)[] = [
      'displayName',
    ];
    if (runtimeDirty && profileReady && !catalog.isError) {
      fieldsToValidate.push(
        ...RUNTIME_FIELD_NAMES,
        'engineArgsYaml',
        'envVarsYaml',
      );
    }
    const valid = await form.trigger(fieldsToValidate);
    if (!valid) return;
    patchMutation.mutate(form.getValues());
  }, [catalog.isError, catalog.isLoading, form, patchMutation, profileReady]);

  const runtimeSubmitDisabled =
    catalog.isLoading ||
    catalog.isError ||
    catalog.accelerators.length === 0 ||
    onboardMutation.isPending;

  const editSaveDisabled = catalog.isLoading || patchMutation.isPending;

  const steps: StepPageStep[] = useMemo(
    () => [
      {
        label: t('stepper.source'),
        content: (
          <StepModelSource
            form={form}
            namespace={namespace}
            readOnly={isEdit}
          />
        ),
        customActions: (
          <div className="flex gap-2">
            <ActionButton
              secondary
              onPress={returnToList}
              data-testid="custom-model-import-cancel"
            >
              {tActions('cancel.title')}
            </ActionButton>
            <ActionButton
              primary
              isLoading={!isEdit && previewMutation.isPending}
              onPress={advanceFromSource}
              data-testid="custom-model-import-next-source"
            >
              {isEdit ? tActions('next') : t('actions.previewAndContinue')}
            </ActionButton>
          </div>
        ),
      },
      {
        label: t('stepper.information'),
        content: (
          <StepModelInformation
            form={form}
            preview={preview}
            existingDisplayNames={existingDisplayNames}
          />
        ),
        customActions: (
          <div className="flex gap-2">
            <ActionButton
              secondary
              onPress={() => goToStep(0)}
              data-testid="custom-model-import-back-information"
            >
              {isEdit ? tActions('back.title') : t('actions.discardChanges')}
            </ActionButton>
            <ActionButton
              primary
              onPress={advanceFromInformation}
              data-testid="custom-model-import-next-information"
            >
              {t('actions.nextRuntime')}
            </ActionButton>
          </div>
        ),
      },
      {
        label: t('stepper.runtime'),
        content: (
          <StepRuntimeProfile
            form={form}
            catalog={catalog}
            isDisabled={runtimeEditBlocked}
            disabledNotice={
              runtimeEditBlocked
                ? t('steps.runtime.profileNotReadyNotice')
                : undefined
            }
          />
        ),
        customActions: (
          <div className="flex gap-2">
            <ActionButton
              secondary
              onPress={() => goToStep(1)}
              data-testid="custom-model-import-back-runtime"
            >
              {tActions('back.title')}
            </ActionButton>
            <ActionButton
              primary
              isLoading={
                isEdit ? patchMutation.isPending : onboardMutation.isPending
              }
              isDisabled={isEdit ? editSaveDisabled : runtimeSubmitDisabled}
              onPress={isEdit ? saveFromEdit : submitFromRuntime}
              data-testid="custom-model-import-submit"
            >
              {isEdit ? tActions('save.title') : t('actions.submit')}
            </ActionButton>
          </div>
        ),
      },
    ],
    [
      advanceFromInformation,
      advanceFromSource,
      catalog,
      editSaveDisabled,
      existingDisplayNames,
      form,
      goToStep,
      isEdit,
      namespace,
      onboardMutation.isPending,
      patchMutation.isPending,
      preview,
      previewMutation.isPending,
      returnToList,
      runtimeEditBlocked,
      runtimeSubmitDisabled,
      saveFromEdit,
      submitFromRuntime,
      t,
      tActions,
    ],
  );

  const showEditError = isEdit && modelQuery.isError;
  const showEditLoading = isEdit && !prefilled && !modelQuery.isError;

  return (
    <div
      className="flex w-full flex-col gap-8 py-6"
      data-testid="custom-model-import-page"
    >
      <header className="flex w-2/3 flex-col gap-3 mx-auto">
        <ActionButton
          tertiary
          size="sm"
          onPress={returnToList}
          icon={<IconArrowLeft size={16} />}
          className="self-start"
          data-testid="custom-model-import-header-back"
        >
          {tActions('back.title')}
        </ActionButton>
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">
            {isEdit ? t('editTitle') : t('title')}
          </h1>
          <p className="text-sm text-default-500">
            {isEdit ? t('editDescription') : t('description')}
          </p>
        </div>
      </header>

      {showEditError ? (
        <div
          className="flex flex-col items-start gap-3"
          data-testid="custom-model-edit-error"
        >
          <p className="text-sm text-danger">{t('errors.loadFailed')}</p>
          <ActionButton secondary onPress={returnToList}>
            {tActions('back.title')}
          </ActionButton>
        </div>
      ) : showEditLoading ? (
        <PageLoader
          label={t('loading')}
          testId="custom-model-edit-loading"
          className="h-64 w-2/3"
        />
      ) : (
        <StepPage
          ref={stepperRef}
          steps={steps}
          stepperClassName="max-w-2/3 md:max-w-1/3 mx-auto"
          contentClassName="w-2/3 mx-auto"
        />
      )}
    </div>
  );
};

export default CustomModelImportPage;
