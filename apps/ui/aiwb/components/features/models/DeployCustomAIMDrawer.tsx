// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';
import { z } from 'zod';

import { useTranslation } from 'next-i18next';

import {
  Divider,
  DrawerForm,
  FormInput,
  FormSwitch,
} from '@amdenterpriseai/components';
import { useSystemToast } from '@amdenterpriseai/hooks';

import { AutoscalingFormFields } from '@/components/features/models/AutoscalingFormFields';
import {
  createAimScalingPolicyConfig,
  DEFAULT_AUTOSCALING,
} from '@/lib/app/aims';
import { deployInference } from '@/lib/app/inference';
import { CustomModelDeployPayload } from '@/types/aims';
import { Model } from '@/types/models';
import { APIRequestError } from '@amdenterpriseai/utils/app';

interface Props {
  model: Model;
  namespace: string;
  /** Source URI of the model weights (AIMModel spec.modelSources[0].sourceUri). */
  sourceUri?: string | null;
  isOpen: boolean;
  onClose: () => void;
  /**
   * Called after a successful deploy, in addition to the drawer's own
   * invalidation of the canonical aim-services list. Consumers use this to
   * refresh their own view (e.g. the custom-models card grid keyed on a
   * different query) without coupling the drawer to a specific list.
   */
  onDeployed?: () => void;
}

const formSchema = z
  .object({
    displayName: z
      .union([z.literal(''), z.string().min(2).max(253)])
      .optional(),
    autoscalingEnabled: z.boolean(),
    minReplicas: z.number().min(1).max(30).optional(),
    maxReplicas: z.number().min(1).max(30).optional(),
    metricQuery: z.string().optional(),
    operationOverTime: z.string().optional(),
    targetType: z.string().optional(),
    targetValue: z.number().min(1).optional(),
  })
  .superRefine((data, ctx) => {
    if (
      data.autoscalingEnabled &&
      data.minReplicas &&
      data.maxReplicas &&
      data.minReplicas > data.maxReplicas
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Min replicas must be less than or equal to max replicas',
        path: ['maxReplicas'],
      });
    }
  });

type DeployCustomFormValues = z.infer<typeof formSchema>;

/**
 * Placeholder for the deploy drawer's future runtime-profile slot.
 *
 * Custom models resolve engine args and env from the namespace AIMProfile /
 * AIMModel state produced by onboarding and model settings — deploy does not
 * send profile overrides; change runtime via edit model settings.
 */
const RuntimeProfileSection = () => <div data-testid="runtime-profile-slot" />;

RuntimeProfileSection.displayName = 'RuntimeProfileSection';

const buildDeployPayload = (
  model: string,
  data: DeployCustomFormValues,
): CustomModelDeployPayload => {
  const payload: CustomModelDeployPayload = {
    model,
    displayName: data.displayName || undefined,
    replicas: 1,
  };
  if (data.autoscalingEnabled) {
    payload.minReplicas = data.minReplicas;
    payload.maxReplicas = data.maxReplicas;
    payload.autoScaling = createAimScalingPolicyConfig({
      metricQuery: data.metricQuery,
      operationOverTime: data.operationOverTime,
      targetType: data.targetType,
      targetValue: data.targetValue,
    });
  }
  return payload;
};

export const DeployCustomAIMDrawer = ({
  model,
  namespace,
  sourceUri,
  isOpen,
  onClose,
  onDeployed,
}: Props) => {
  const { t } = useTranslation('models');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();
  const modelResourceName = model.resourceName ?? model.id ?? '';
  const defaultValues = useMemo<DeployCustomFormValues>(
    () => ({
      displayName: '',
      autoscalingEnabled: false,
      ...DEFAULT_AUTOSCALING,
    }),
    [],
  );

  const deployMutation = useMutation({
    mutationFn: (data: DeployCustomFormValues) =>
      deployInference(namespace, buildDeployPayload(modelResourceName, data)),
    onSuccess: () => {
      toast.success(t('deployCustomAIMDrawer.notifications.success'));
      // FineTuneModels' table reads this key; invalidate it so the deployed
      // AIM services refresh after a successful deploy.
      queryClient.invalidateQueries({
        queryKey: ['project', namespace, 'aim-services'],
      });
      queryClient.invalidateQueries({ queryKey: ['inferenceModel'] });
      onDeployed?.();
      onClose();
    },
    onError: (error: Error) => {
      // Keep the drawer open with the user's values intact so they can retry.
      toast.error(
        t('deployCustomAIMDrawer.notifications.error', {
          message:
            error instanceof APIRequestError ? error.message : 'Unknown error',
        }),
      );
    },
  });

  const handleDeploy = useCallback(
    (data: DeployCustomFormValues) => {
      deployMutation.mutate(data);
    },
    [deployMutation],
  );

  return (
    <DrawerForm<DeployCustomFormValues>
      isOpen={isOpen}
      onCancel={onClose}
      onFormSuccess={handleDeploy}
      onFormFailure={() => {}}
      title={t('deployCustomAIMDrawer.title')}
      confirmText={t('deployCustomAIMDrawer.actions.deploy')}
      cancelText={t('deployCustomAIMDrawer.actions.cancel')}
      validationSchema={formSchema}
      isActioning={deployMutation.isPending}
      isDisabled={deployMutation.isPending}
      hideCloseButton={false}
      defaultValues={defaultValues}
      renderFields={(form) => (
        <div className="flex flex-col gap-4 mt-4">
          <div className="flex flex-col gap-1">
            <p className="text-small text-default-500">
              {t('deployCustomAIMDrawer.header.deployingInto', { namespace })}
            </p>
            <div className="text-2xl font-bold">{model.name}</div>
            {model.canonicalName && (
              <p className="text-default-500">{model.canonicalName}</p>
            )}
            {sourceUri && (
              <p className="text-small text-default-500 wrap-break-words mt-1">
                <span className="text-default-400">
                  {t('deployCustomAIMDrawer.header.sourceUri')}:
                </span>{' '}
                {sourceUri}
              </p>
            )}
          </div>

          <Divider />

          <FormInput<DeployCustomFormValues>
            name="displayName"
            form={form}
            label={t('deployCustomAIMDrawer.fields.displayName.title')}
            placeholder={t(
              'deployCustomAIMDrawer.fields.displayName.placeholder',
            )}
            description={t('deployCustomAIMDrawer.fields.displayName.helper')}
          />

          <RuntimeProfileSection />

          {/* ====== AUTOSCALING SECTION ====== */}
          <Divider />
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-1">
              <h3 className="text-medium font-medium text-foreground">
                {t('deployCustomAIMDrawer.fields.autoscaling.title')}
              </h3>
            </div>
            <div className="flex flex-col gap-0">
              <FormSwitch
                form={form}
                name="autoscalingEnabled"
                data-testid="autoscaling-toggle"
              >
                {t('deployCustomAIMDrawer.fields.autoscaling.enable')}
              </FormSwitch>
              <p role="note" className="text-small text-default-500 ml-[58px]">
                {t('helper', { ns: 'autoscaling' })}
              </p>
            </div>
            {form.watch('autoscalingEnabled') && (
              <AutoscalingFormFields
                form={form}
                className="flex flex-col gap-4 pl-1"
              />
            )}
          </div>
        </div>
      )}
    />
  );
};

DeployCustomAIMDrawer.displayName = 'DeployCustomAIMDrawer';
