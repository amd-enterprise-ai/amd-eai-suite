// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Input } from '@heroui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { z } from 'zod';

import { useTranslation } from 'next-i18next';

import { DrawerForm } from '@amdenterpriseai/components';
import { useSystemToast } from '@amdenterpriseai/hooks';

import { deployAim } from '@/lib/app/aims';
import { Model } from '@/types/models';
import { APIRequestError } from '@amdenterpriseai/utils/app';

interface Props {
  model: Model;
  namespace: string;
  isOpen: boolean;
  onClose: () => void;
}

const formSchema = z.object({});

type DeployFinetuneFormValues = z.infer<typeof formSchema>;

export const DeployFinetuneAIMDrawer = ({
  model,
  namespace,
  isOpen,
  onClose,
}: Props) => {
  const { t } = useTranslation('models');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const modelResourceName = model.resourceName ?? model.id ?? '';

  const deployMutation = useMutation({
    mutationFn: () =>
      deployAim(namespace, {
        model: modelResourceName,
        allowUnoptimized: true,
      }),
    onSuccess: () => {
      toast.success(t('deployFinetuneAIMDrawer.notifications.success'));
      queryClient.invalidateQueries({
        queryKey: ['project', namespace, 'aims', 'services'],
      });
      onClose();
    },
    onError: (error: Error) => {
      toast.error(
        t('deployFinetuneAIMDrawer.notifications.error', {
          message:
            error instanceof APIRequestError ? error.message : 'Unknown error',
        }),
      );
    },
  });

  const handleDeploy = useCallback(() => {
    deployMutation.mutate();
  }, [deployMutation]);

  return (
    <DrawerForm<DeployFinetuneFormValues>
      isOpen={isOpen}
      onCancel={onClose}
      onFormSuccess={handleDeploy}
      onFormFailure={() => {}}
      title={t('deployFinetuneAIMDrawer.title')}
      confirmText={t('deployFinetuneAIMDrawer.actions.deploy')}
      cancelText={t('deployFinetuneAIMDrawer.actions.cancel')}
      validationSchema={formSchema}
      isActioning={deployMutation.isPending}
      isDisabled={deployMutation.isPending}
      hideCloseButton={false}
      defaultValues={{}}
      renderFields={() => (
        <div className="flex flex-col gap-4 mt-4">
          <div>
            <div className="text-2xl font-bold">{model.name}</div>
            <p className="text-default-500">{model.canonicalName}</p>
          </div>

          <Input
            label={t('deployFinetuneAIMDrawer.fields.name.label')}
            description={t('deployFinetuneAIMDrawer.fields.name.description')}
            labelPlacement="outside"
            variant="bordered"
            value={modelResourceName}
            isReadOnly
            isDisabled
          />
        </div>
      )}
    />
  );
};

DeployFinetuneAIMDrawer.displayName = 'DeployFinetuneAIMDrawer';
