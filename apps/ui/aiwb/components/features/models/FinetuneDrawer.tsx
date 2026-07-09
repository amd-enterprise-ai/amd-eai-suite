// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Accordion,
  AccordionItem,
  SelectItem,
  Divider,
  FormInput,
  FormNumberInput,
  FormSelect,
  DrawerForm,
  Spinner,
} from '@amdenterpriseai/components';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';
import { UseFormReturn } from 'react-hook-form';

import { useTranslation } from 'next-i18next';

import { getAllDatasets } from '@/lib/app/datasets';
import { listProjectFineTunedModels } from '@/lib/app/models';
import { fetchAllPages } from '@/lib/app/pagination';
import { listAllWorkloads } from '@/lib/app/workloads';
import { useProject } from '@/contexts/ProjectContext';
import { useSystemToast } from '@amdenterpriseai/hooks';

import { createHuggingFaceSecretRequest } from '@/lib/app/huggingface-secret';

import { Dataset } from '@/types/datasets';
import { DatasetType } from '@/types/datasets';
import { SecretUseCase } from '@amdenterpriseai/types';
import { AIM_MODEL_NAME_LABEL, AIMModel } from '@/types/aims';
import { FinetunableModel, Model, ModelFinetuneParams } from '@/types/models';
import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';

import { debounce } from 'lodash';
import { z } from 'zod';
import { SecretResponseData } from '@/types/secrets';
import { createProjectSecret, fetchProjectSecrets } from '@/lib/app/secrets';
import { validateHuggingFaceTokenFields } from '@/lib/app/huggingface-secret';
import { HuggingFaceTokenSelector } from '@/components/shared/HuggingFaceTokenSelector';

interface FinetuneDrawerProps {
  isOpen: boolean;
  model: Model | undefined;
  finetunableModels: FinetunableModel[];
  onOpenChange: () => void;
  onConfirmAction: (param: { id: string; params: ModelFinetuneParams }) => void;
}

const getRecipeGpuCount = (
  finetunableModels: FinetunableModel[],
  canonicalName: string | undefined,
  model: Model | undefined,
): number | undefined =>
  finetunableModels.find(
    (m) => m.canonicalName === (canonicalName || model?.canonicalName),
  )?.gpuCount || undefined;

/**
 * Resolve whether the model selected for fine-tuning needs a Hugging Face token.
 *
 * Prefers the model's own `hfTokenRequired` flag, then the source recipe's
 * requirement (looked up by canonical name). Defaults to not gated, since a
 * re-finetune of weights already in S3 needs no token.
 */
const isBaseModelGated = (
  finetunableModels: FinetunableModel[],
  canonicalName: string | undefined,
  model: Model | undefined,
): boolean => {
  if (model?.hfTokenRequired != null) return model.hfTokenRequired;
  const found = finetunableModels.find(
    (m) => m.canonicalName === (canonicalName || model?.canonicalName),
  );
  return found?.hfTokenRequired === true;
};

const FinetuneDrawer = ({
  isOpen,
  model,
  finetunableModels,
  onOpenChange,
  onConfirmAction,
}: FinetuneDrawerProps) => {
  const { t } = useTranslation('models', { keyPrefix: 'customModels' });
  const { t: tHf } = useTranslation('models');
  const { activeProject } = useProject();
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();
  const { data: datasets = [] } = useQuery({
    queryKey: ['project', activeProject, 'datasets'],
    queryFn: (): Promise<Dataset[]> =>
      getAllDatasets(activeProject!, { type: DatasetType.Finetuning }),
    enabled: isOpen && !!activeProject,
  });

  const { data: projectSecrets } = useQuery<SecretResponseData[]>({
    queryKey: ['project', activeProject, 'secrets'],
    queryFn: async () => {
      const response = await fetchProjectSecrets(activeProject!);
      return response.data;
    },
    enabled: isOpen && !!activeProject,
  });

  const huggingFaceTokens =
    projectSecrets?.filter((ps) => ps.useCase === SecretUseCase.HUGGING_FACE) ??
    [];

  const createSecretMutation = useMutation({
    mutationFn: (secretRequest: Parameters<typeof createProjectSecret>[1]) =>
      createProjectSecret(activeProject!, secretRequest),
    onSuccess: (createdSecret: SecretResponseData, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'secrets'],
      });

      toast.success(
        tHf('huggingFaceTokenDrawer.notifications.secretCreated', {
          name: variables.displayName,
        }),
      );
    },
    onError: (error: Error) => {
      toast.error(
        tHf('huggingFaceTokenDrawer.notifications.secretCreateError', {
          error: error.message,
        }),
      );
    },
  });

  const [uniqueCheckInProgress, setUniqueCheckInProgress] =
    useState<boolean>(false);

  const apiCheck = useCallback(
    async (name: string, resolve: (result: boolean) => void) => {
      setUniqueCheckInProgress(true);
      try {
        const [models, workloads] = await Promise.all([
          queryClient.fetchQuery({
            queryKey: ['project', activeProject, 'models', 'name-check'],
            // Walk via fetchAllPages directly so errors propagate to the
            // catch block. Using listAllProjectFineTunedModels here would
            // swallow failures (returns []), letting a duplicate name slip
            // through during backend outages.
            queryFn: () =>
              fetchAllPages<AIMModel>((page, pageSize) =>
                listProjectFineTunedModels(activeProject!, { page, pageSize }),
              ),
            staleTime: 0,
          }),
          queryClient.fetchQuery({
            queryKey: ['project', activeProject, 'workloads', 'name-check'],
            queryFn: () =>
              listAllWorkloads(activeProject!, {
                type: [WorkloadType.FINE_TUNING],
                status: [
                  WorkloadStatus.PENDING,
                  WorkloadStatus.STARTING,
                  WorkloadStatus.RUNNING,
                ],
              }),
            staleTime: 0,
          }),
        ]);

        const completedModelExists = models.some(
          (m) => m.metadata?.labels?.[AIM_MODEL_NAME_LABEL] === name,
        );
        const inProgressJobExists = workloads.some(
          (w) => w.displayName === name,
        );

        resolve(!completedModelExists && !inProgressJobExists);
      } catch (error) {
        console.error('Error checking model name availability:', error);
        resolve(true);
      } finally {
        setUniqueCheckInProgress(false);
      }
    },
    [queryClient, activeProject],
  );

  const debouncedApiCheck = useMemo(() => debounce(apiCheck, 700), [apiCheck]);

  const validateModelName = useCallback(
    (desiredName: string): Promise<boolean> => {
      if (!desiredName || desiredName.trim().length === 0)
        return Promise.resolve(false);

      return new Promise((resolve) => {
        debouncedApiCheck(desiredName, resolve);
      });
    },
    [debouncedApiCheck],
  );

  const formSchema = useMemo(
    () =>
      z
        .object({
          displayName: z
            .string()
            .trim()
            .nonempty({
              message: t(
                'list.actions.finetune.modal.modelName.emptyNameError',
              ),
            })
            .refine(async (name) => validateModelName(name), {
              message: t(
                'list.actions.finetune.modal.modelName.nonUniqueNameError',
              ),
            }),
          description: z.string().trim().optional(),
          canonicalName: z.string().trim().optional(),
          baseModelId: z.string().trim().optional(),
          datasetId: z.string().trim(),
          selectedToken: z.string().optional(),
          tokenName: z.string().optional(),
          token: z.string().optional(),
          epochs: z.number().int().nonnegative().min(1).max(10).optional(),
          learningRate: z.number().nonnegative().min(0.1).max(10).optional(),
          batchSize: z.number().int().nonnegative().min(1).max(128).optional(),
        })
        .superRefine((data, ctx) => {
          const selectedCanonicalName =
            data.canonicalName || model?.canonicalName;
          // Skip validation until a base model is selected, and when the selected model is not gated.
          if (
            !selectedCanonicalName ||
            !isBaseModelGated(finetunableModels, selectedCanonicalName, model)
          )
            return;
          // If user selected an existing token or is training local model, validation passes
          // otherwise validate HF token
          if (data.selectedToken || model?.sourceUri) return;
          validateHuggingFaceTokenFields(data, ctx, tHf);
        }),
    [t, tHf, validateModelName, model, finetunableModels],
  );

  const formDefaultValues = useMemo(
    () => ({
      displayName: '',
      description: '',
      canonicalName: '',
      baseModelId: '',
      datasetId: '',
      selectedToken: '',
      tokenName: '',
      token: '',
      epochs: undefined,
      learningRate: undefined,
      batchSize: undefined,
    }),
    [],
  );

  const submitFinetuneModel = async (data: any) => {
    // Helper function to build and submit finetune params
    const buildAndSubmitParams = (hfTokenSecretName?: string) => {
      const finetuneParams: ModelFinetuneParams = {
        displayName: data.displayName as string,
        datasetId: data.datasetId as string,
        epochs: data.epochs,
        learningRate: data.learningRate,
        batchSize: data.batchSize,
      };

      if (hfTokenSecretName) {
        finetuneParams.hfTokenSecretName = hfTokenSecretName;
      }

      onConfirmAction({
        id: model?.id ?? model?.resourceName ?? data.canonicalName,
        params: finetuneParams,
      });
      onOpenChange();
    };

    // If model is available locally or is not gated, skip HF token processing
    if (
      model?.sourceUri ||
      !isBaseModelGated(finetunableModels, data.canonicalName, model)
    ) {
      buildAndSubmitParams();
      return;
    }

    // Otherwise, process HF token for gated canonical name fine-tuning
    const isNewToken = !data.selectedToken && data.tokenName && data.token;

    if (isNewToken) {
      const request = createHuggingFaceSecretRequest(
        data.tokenName!,
        data.token!,
      );

      createSecretMutation.mutateAsync(request as any, {
        onSuccess: (createdSecret: SecretResponseData) => {
          if (!createdSecret || !createdSecret.metadata.name) {
            toast.error(
              tHf('huggingFaceTokenDrawer.notifications.invalidSecretResponse'),
            );
            return;
          }

          buildAndSubmitParams(createdSecret.metadata.name);
        },
      });
    } else {
      // HuggingFaceTokenSelector stores the selected token's list index as a
      // string; an empty value means nothing was picked.
      const selectedToken = huggingFaceTokens[parseInt(data.selectedToken, 10)];

      if (!selectedToken) {
        toast.error(
          tHf('huggingFaceTokenDrawer.notifications.noTokenSelected'),
        );
        return;
      }

      buildAndSubmitParams(selectedToken.metadata.name);
    }
  };

  return (
    <DrawerForm
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      title={t('list.actions.finetune.modal.title') as string}
      confirmText={t('list.actions.finetune.modal.confirm')}
      cancelText={t('list.actions.finetune.modal.cancel')}
      validationSchema={formSchema}
      onCancel={onOpenChange}
      onFormSuccess={submitFinetuneModel}
      defaultValues={formDefaultValues}
      renderFields={(form: UseFormReturn<any>) => (
        <div className="flex flex-col gap-4">
          <FormInput
            form={form}
            name="displayName"
            label={t('list.actions.finetune.modal.modelName.label')}
            placeholder={t('list.actions.finetune.modal.modelName.placeholder')}
            description={t('list.actions.finetune.modal.modelName.description')}
            isRequired
            endContent={
              uniqueCheckInProgress && <Spinner size="sm" color="primary" />
            }
          />
          <FormSelect
            form={form}
            disallowEmptySelection
            isDisabled={!!model || finetunableModels.length === 0}
            isRequired
            name="canonicalName"
            label={t('list.actions.finetune.modal.baseModel.label')}
            placeholder={
              model
                ? model.name
                : finetunableModels.length === 0
                  ? t(
                      'list.actions.finetune.modal.baseModel.noCompatibleRecipes',
                    )
                  : t('list.actions.finetune.modal.baseModel.placeholder')
            }
            data-testid="baseModelSelect"
            onSelectionChange={() => {
              form.setValue('batchSize', undefined, { shouldValidate: true });
            }}
          >
            {finetunableModels.map((finetunableModel: FinetunableModel) => (
              <SelectItem
                key={finetunableModel.canonicalName}
                data-testid={`model-select-${finetunableModel.canonicalName}`}
                description={
                  finetunableModel.compatibleAcceleratorNames.length > 0
                    ? finetunableModel.compatibleAcceleratorNames.join(', ')
                    : undefined
                }
              >
                {finetunableModel.canonicalName}
              </SelectItem>
            ))}
          </FormSelect>
          <FormSelect
            form={form}
            disallowEmptySelection
            isRequired
            name="datasetId"
            label={t('list.actions.finetune.modal.dataset.label')}
            placeholder={t('list.actions.finetune.modal.dataset.placeholder')}
            data-testid="datasetSelect"
          >
            {datasets !== undefined
              ? datasets?.map((dataset) => (
                  <SelectItem
                    key={dataset.id}
                    data-testid={`dataset-select-${dataset.id}`}
                  >
                    {dataset.name}
                  </SelectItem>
                ))
              : null}
          </FormSelect>

          <FormInput
            form={form}
            name="description"
            label={t('list.actions.finetune.modal.modelDescription.label')}
            placeholder={t(
              'list.actions.finetune.modal.modelDescription.placeholder',
            )}
          />

          {/* Only show the HF Token section for gated base models, never for
              local weights. In the recipe-list flow it stays hidden until a
              base model is picked; a pre-selected model always has one. */}
          {!model?.sourceUri &&
            (form.watch('canonicalName') || !!model) &&
            isBaseModelGated(
              finetunableModels,
              form.watch('canonicalName'),
              model,
            ) && (
              <>
                {/* Divider */}
                <Divider className="my-2" />

                {/* Hugging Face Authentication Section */}
                <div className="flex flex-col gap-4">
                  <h4 className="font-semibold">
                    {tHf('huggingFaceTokenDrawer.title')}
                  </h4>
                  <HuggingFaceTokenSelector
                    form={form}
                    existingTokens={huggingFaceTokens}
                    fieldNames={{
                      selectedToken: 'selectedToken',
                      name: 'tokenName',
                      token: 'token',
                    }}
                  />
                </div>
              </>
            )}

          <Accordion className="px-0">
            <AccordionItem
              title={t(
                'list.actions.finetune.modal.advancedSettingsAccordion.title',
              )}
              classNames={{
                base: 'px-0',
                trigger: 'px-0 cursor-pointer',
                content: 'flex flex-col gap-4 px-0',
              }}
            >
              <FormNumberInput
                form={form}
                name="batchSize"
                label={t('list.actions.finetune.modal.batchSize.label')}
                placeholder={t(
                  'list.actions.finetune.modal.batchSize.placeholder',
                )}
                description={t(
                  'list.actions.finetune.modal.batchSize.description',
                )}
                isDisabled={
                  !(form.watch('canonicalName') || model?.canonicalName)
                }
                value={form.watch('batchSize') ?? NaN}
                step={getRecipeGpuCount(
                  finetunableModels,
                  form.watch('canonicalName'),
                  model,
                )}
                minValue={getRecipeGpuCount(
                  finetunableModels,
                  form.watch('canonicalName'),
                  model,
                )}
                maxValue={128}
                isClearable
              />
              <FormNumberInput
                form={form}
                name="epochs"
                label={t('list.actions.finetune.modal.epochs.label')}
                placeholder={t(
                  'list.actions.finetune.modal.epochs.placeholder',
                )}
                description={t(
                  'list.actions.finetune.modal.epochs.description',
                )}
                minValue={1}
                maxValue={10}
                isClearable
              />
              <FormNumberInput
                form={form}
                name="learningRate"
                label={t(
                  'list.actions.finetune.modal.learningRateMultiplier.label',
                )}
                placeholder={t(
                  'list.actions.finetune.modal.learningRateMultiplier.placeholder',
                )}
                description={t(
                  'list.actions.finetune.modal.learningRateMultiplier.description',
                )}
                step={0.1}
                minValue={0.1}
                maxValue={10}
                isClearable
              />
            </AccordionItem>
          </Accordion>
        </div>
      )}
    />
  );
};

export default FinetuneDrawer;
