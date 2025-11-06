// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Divider, Tooltip } from '@heroui/react';
import { IconInfoCircle } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';
import { UseFormReturn } from 'react-hook-form';
import { z } from 'zod';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { deployAim } from '@/services/app/aims';
import { createSecret, fetchProjectSecrets } from '@/services/app/secrets';
import {
  createHuggingFaceSecretRequest,
  isValidHuggingFaceToken,
} from '@/utils/app/huggingface-secret';

import { Aim } from '@/types/aims';
import { SecretUseCase } from '@/types/enums/secrets';
import { ProjectSecretWithParentSecret, Secret } from '@/types/secrets';

import { HuggingFaceTokenSelector } from '@/components/shared/HuggingFaceTokenSelector';

import { ModelIcon } from '@/components/shared/ModelIcons';
import { DrawerForm } from '@/components/shared/DrawerForm';

import { useProject } from '@/contexts/ProjectContext';

interface DeployAIMFormValues {
  selectedToken?: string;
  tokenName?: string;
  token?: string;
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
    mutationFn: (secretRequest: Parameters<typeof createSecret>[0]) =>
      createSecret(secretRequest),
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
        })
        .superRefine((data, ctx) => {
          // Skip HF token validation if not required
          if (!aim.isHfTokenRequired) return;

          const hasSelectedToken =
            data.selectedToken && data.selectedToken.trim() !== '';
          const hasTokenName = data.tokenName && data.tokenName.trim() !== '';
          const hasToken = data.token && data.token.trim() !== '';

          if (hasSelectedToken) return;

          if (!hasTokenName && !hasToken) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('huggingFaceTokenDrawer.validation.tokenRequired'),
              path: ['selectedToken'],
            });
            return;
          }

          // User has started creating a new token, validate both fields
          if (!hasTokenName) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('huggingFaceTokenDrawer.validation.nameRequired'),
              path: ['tokenName'],
            });
          } else if (hasTokenName) {
            // Validate token name pattern
            const tokenNamePattern = /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/;
            if (!tokenNamePattern.test(data.tokenName!.trim())) {
              ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: t(
                  'huggingFaceTokenDrawer.validation.invalidSecretName',
                ),
                path: ['tokenName'],
              });
            }
          }
          if (!hasToken) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('huggingFaceTokenDrawer.validation.tokenRequired'),
              path: ['token'],
            });
          } else if (!isValidHuggingFaceToken(data.token!)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t(
                'huggingFaceTokenDrawer.validation.invalidTokenFormat',
              ),
              path: ['token'],
            });
          }
        }),
    [t, aim.isHfTokenRequired],
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

          const payload: {
            cacheModel: boolean;
            replicas: number;
            hfToken?: string;
          } = {
            cacheModel: true,
            replicas: 1,
          };

          if (hfTokenName) {
            payload.hfToken = hfTokenName;
          }

          await deployAim(aim.id, activeProjectId, payload);
          if (onClose) onClose();
          toast.success(t('deployAIMDrawer.notifications.success'));
          if (onDeploying) onDeploying();
        } catch (error) {
          toast.error(t('deployAIMDrawer.notifications.error'));
          console.error(t('deployAIMDrawer.notifications.error'), error);
        } finally {
          setIsDeploying(false);
        }
      };

      if (isNewToken) {
        const secretRequest = createHuggingFaceSecretRequest(
          data.tokenName!,
          data.token!,
          [activeProjectId],
        );

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
    <>
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
        }}
        renderFields={(form) => {
          formRef.current = form;

          return (
            <div className="flex flex-col gap-4 mt-4">
              <div className="flex justify-between items-top">
                <div>
                  <div className="text-2xl font-bold">{aim?.title}</div>
                  <div className="text-gray-500">{aim?.description.short}</div>
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
            </div>
          );
        }}
      />
    </>
  );
};

DeployAIMDrawer.displayName = 'DeployAIMDrawer';
