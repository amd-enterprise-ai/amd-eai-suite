// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Divider, SelectItem, Switch, Tooltip } from '@heroui/react';
import { IconInfoCircle } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';
import { Controller, UseFormReturn } from 'react-hook-form';
import { z } from 'zod';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { deployAim } from '@/services/app/aims';
import {
  createProjectSecret,
  fetchProjectSecrets,
} from '@/services/app/secrets';
import {
  createHuggingFaceSecretRequest,
  validateHuggingFaceTokenFields,
} from '@/utils/app/huggingface-secret';

import { Aim, AimDeployPayload } from '@/types/aims';
import { SecretType, SecretUseCase } from '@/types/enums/secrets';
import { ProjectSecretWithParentSecret, Secret } from '@/types/secrets';

import { HuggingFaceTokenSelector } from '@/components/shared/HuggingFaceTokenSelector';

import { ModelIcon } from '@/components/shared/ModelIcons';
import { DrawerForm } from '@/components/shared/Drawer';
import { FormSelect } from '@/components/shared/ManagedForm/FormSelect';

import { useProject } from '@/contexts/ProjectContext';
import { APIRequestError } from '@/utils/app/errors';

interface DeployAIMFormValues {
  selectedToken?: string;
  tokenName?: string;
  token?: string;
  metric?: string;
  allowUnoptimized: boolean;
}

interface Props {
  isOpen: boolean;
  onClose?: () => void;
  onDeployed?: () => void;
  onDeploying?: () => void;
  aim: Aim;
}

export const DeployAIMDrawer = ({
  isOpen,
  onClose,
  onDeploying,
  aim,
}: Props) => {
  const { t } = useTranslation('models');
  const { toast } = useSystemToast();
  const { activeProject: activeProjectId } = useProject();
  const queryClient = useQueryClient();

  const [isDeploying, setIsDeploying] = useState(false);

  const formRef = useRef<UseFormReturn<DeployAIMFormValues> | null>(null);

  const { data: projectSecrets } = useQuery<ProjectSecretWithParentSecret[]>({
    queryKey: ['project', activeProjectId, 'secrets'],
    queryFn: async () => {
      const response = await fetchProjectSecrets(activeProjectId!);
      return response.projectSecrets;
    },
    enabled: !!activeProjectId && isOpen,
  });

  const huggingFaceTokens = useMemo(() => {
    if (!projectSecrets) return [];
    return projectSecrets
      .filter((ps) => ps.secret.useCase === SecretUseCase.HUGGING_FACE)
      .map((ps) => ({
        id: ps.secret.id,
        name: ps.secret.displayName || ps.secret.name,
      }));
  }, [projectSecrets]);

  const createSecretMutation = useMutation({
    mutationFn: (secretRequest: Parameters<typeof createProjectSecret>[1]) =>
      createProjectSecret(activeProjectId!, secretRequest),
    onSuccess: (createdSecret: Secret, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProjectId, 'secrets'],
      });

      toast.success(
        t('huggingFaceTokenDrawer.notifications.secretCreated', {
          name: variables.name,
        }),
      );
    },
    onError: (error: Error) => {
      toast.error(
        t('huggingFaceTokenDrawer.notifications.secretCreateError', {
          error: error.message,
        }),
      );
    },
  });

  const formSchema = useMemo(
    () =>
      z
        .object({
          selectedToken: z.string().optional(),
          tokenName: z.string().optional(),
          token: z.string().optional(),
          metric: z.string().optional(),
          allowUnoptimized: z.boolean(),
        })
        .superRefine((data, ctx) => {
          validateHuggingFaceTokenFields(data, ctx, {
            isRequired: aim.isHfTokenRequired,
            projectSecrets,
            t,
          });
        }),
    [t, aim.isHfTokenRequired, projectSecrets],
  );

  const handleDeploy = useCallback(
    async (data: DeployAIMFormValues) => {
      if (!activeProjectId) {
        toast.error(t('deployAIMDrawer.notifications.noProjectError'));
        return;
      }

      const isNewToken =
        aim.isHfTokenRequired &&
        !data.selectedToken &&
        data.tokenName &&
        data.token;

      const buildAndSubmitDeploy = async (hfTokenName?: string) => {
        try {
          setIsDeploying(true);

          const payload: AimDeployPayload = {
            cacheModel: true,
            replicas: 1,
            allowUnoptimized: data.allowUnoptimized,
          };

          if (hfTokenName) {
            payload.hfToken = hfTokenName;
          }

          if (data.metric) {
            payload.metric = data.metric;
          }

          await deployAim(aim.id, activeProjectId, payload);
          if (onClose) onClose();
          toast.success(t('deployAIMDrawer.notifications.success'));
          if (onDeploying) onDeploying();
        } catch (error) {
          toast.error(
            t('deployAIMDrawer.notifications.error', {
              message: (error as APIRequestError).message || 'Unknown error',
            }),
            error as APIRequestError,
          );
        } finally {
          setIsDeploying(false);
        }
      };

      if (isNewToken) {
        const secretRequestWithProjectIds = createHuggingFaceSecretRequest(
          data.tokenName!,
          data.token!,
          [activeProjectId],
        );

        // Remove project_ids since createProjectSecret handles the project association
        const { project_ids: _project_ids, ...secretRequest } =
          secretRequestWithProjectIds;

        createSecretMutation.mutate(secretRequest, {
          onSuccess: (createdSecret: Secret) => {
            if (!createdSecret || !createdSecret.name) {
              toast.error(
                t('huggingFaceTokenDrawer.notifications.invalidSecretResponse'),
              );
              setIsDeploying(false);
              return;
            }

            buildAndSubmitDeploy(createdSecret.name);
          },
          onError: () => {
            setIsDeploying(false);
          },
        });
      } else if (aim.isHfTokenRequired && data.selectedToken) {
        const selectedTokenId = data.selectedToken;

        // Find the token name from the selected token ID
        const selectedToken = huggingFaceTokens.find(
          (token) => token.id === selectedTokenId,
        );

        if (!selectedToken) {
          toast.error(
            t('huggingFaceTokenDrawer.notifications.noTokenSelected'),
          );
          return;
        }

        buildAndSubmitDeploy(selectedToken.name);
      } else {
        // No token provided or not required - deploy without hfToken
        buildAndSubmitDeploy();
      }
    },
    [
      activeProjectId,
      aim.id,
      aim.isHfTokenRequired,
      onClose,
      onDeploying,
      t,
      toast,
      createSecretMutation,
      huggingFaceTokens,
    ],
  );

  const isDeployDisabled = isDeploying;

  return (
    <DrawerForm<DeployAIMFormValues>
      isOpen={isOpen}
      onCancel={onClose}
      onFormSuccess={handleDeploy}
      title={t('deployAIMDrawer.title')}
      confirmText={t('deployAIMDrawer.actions.deploy')}
      validationSchema={formSchema}
      cancelText={t('deployAIMDrawer.actions.cancel')}
      isActioning={isDeploying}
      isDisabled={isDeployDisabled}
      hideCloseButton={false}
      defaultValues={{
        selectedToken: '',
        tokenName: '',
        token: '',
        metric: '',
        allowUnoptimized: false,
      }}
      renderFields={(form) => {
        formRef.current = form;

        return (
          <div className="flex flex-col gap-4 mt-4">
            <div className="flex justify-between items-top">
              <div>
                <div className="text-2xl font-bold">{aim?.title}</div>
                <p>{aim?.description.short}</p>
              </div>

              <div className="w-12 h-12">
                <ModelIcon
                  iconName={aim.canonicalName}
                  width={48}
                  height={48}
                />
              </div>
            </div>
            <p className="whitespace-pre-wrap break-words">
              {aim?.description.full}
            </p>
            <Divider />
            <div className="text-foreground text-medium uppercase font-bold">
              {t('deployAIMDrawer.fields.title')}
            </div>
            {aim.isHfTokenRequired && (
              <>
                <div className="flex items-center gap-1">
                  <h3 className="text-medium font-medium text-foreground">
                    {t('deployAIMDrawer.fields.huggingFaceToken.title')}
                  </h3>
                  <Tooltip
                    classNames={{
                      content: 'max-w-md',
                    }}
                    content={t(
                      'deployAIMDrawer.fields.huggingFaceToken.description',
                    )}
                  >
                    <IconInfoCircle
                      className="text-default-400 cursor-pointer"
                      size={16}
                    />
                  </Tooltip>
                </div>
                <HuggingFaceTokenSelector
                  form={form}
                  existingTokens={huggingFaceTokens}
                  fieldNames={{
                    selectedToken: 'selectedToken',
                    name: 'tokenName',
                    token: 'token',
                  }}
                />
              </>
            )}
            {aim.availableMetrics.length > 0 && (
              <>
                <div className="flex items-center gap-1">
                  <h3 className="text-medium font-medium text-foreground">
                    {t('deployAIMDrawer.fields.metric.title')}
                  </h3>
                  <Tooltip
                    classNames={{
                      content: 'max-w-md whitespace-pre-line',
                    }}
                    content={t('deployAIMDrawer.fields.metric.description')}
                  >
                    <IconInfoCircle
                      className="text-default-400 cursor-pointer"
                      size={16}
                    />
                  </Tooltip>
                </div>
                <FormSelect
                  name="metric"
                  form={form}
                  aria-label={t('deployAIMDrawer.fields.metric.label')}
                  placeholder={t('deployAIMDrawer.fields.metric.placeholder')}
                  classNames={{
                    value: 'capitalize',
                  }}
                >
                  {aim.availableMetrics.map((metric) => (
                    <SelectItem key={metric} className="capitalize">
                      {metric}
                    </SelectItem>
                  ))}
                </FormSelect>
              </>
            )}

            {/* Experimental Deployment Section */}
            <div className="flex items-center gap-1">
              <h3 className="text-medium font-medium text-foreground">
                {t('deployAIMDrawer.fields.experimentalDeployment.title')}
              </h3>
              <Tooltip
                classNames={{
                  content: 'max-w-md whitespace-pre-line',
                }}
                content={t(
                  'deployAIMDrawer.fields.experimentalDeployment.description',
                )}
              >
                <IconInfoCircle
                  className="text-default-400 cursor-pointer"
                  size={16}
                />
              </Tooltip>
            </div>
            <Controller
              name="allowUnoptimized"
              control={form.control}
              render={({ field }) => (
                <Switch isSelected={field.value} onValueChange={field.onChange}>
                  {t('deployAIMDrawer.fields.experimentalDeployment.label')}
                </Switch>
              )}
            />
          </div>
        );
      }}
    />
  );
};

DeployAIMDrawer.displayName = 'DeployAIMDrawer';
