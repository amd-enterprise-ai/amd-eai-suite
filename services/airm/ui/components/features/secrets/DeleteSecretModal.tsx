// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'next-i18next';
import useSystemToast from '@/hooks/useSystemToast';
import { deleteProjectSecret, deleteSecret } from '@/services/app/secrets';
import { APIRequestError } from '@/utils/app/errors';
import { BaseSecret, Secret } from '@/types/secrets';
import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';

interface Props {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  secret: Secret | BaseSecret | null;
  projectId?: string;
  queryKeyToInvalidate: string[];
}

export default function DeleteSecretModal({
  isOpen,
  onOpenChange,
  secret,
  projectId,
  queryKeyToInvalidate,
}: Props) {
  const { t } = useTranslation('secrets');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const formKey = projectId ? 'deleteProjectSecret' : 'delete';
  const { mutate: deleteSecretAction, isPending } = useMutation({
    mutationFn: async () => {
      if (!secret) {
        throw new Error('Secret is null');
      }
      if (projectId) {
        return deleteProjectSecret(projectId, secret.id);
      }
      return deleteSecret(secret.id);
    },
    onSuccess: () => {
      toast.success(t(`form.${formKey}.notification.success`));
      queryClient.invalidateQueries({ queryKey: ['secrets'] });
      if (projectId) {
        queryClient.invalidateQueries({
          queryKey: ['projectSecrets', projectId],
        });
      }
      queryClient.invalidateQueries({ queryKey: queryKeyToInvalidate });
      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(
        t(`form.${formKey}.notification.error`),
        error as APIRequestError,
      );
    },
  });

  if (!secret) return null;

  return (
    <ConfirmationModal
      confirmationButtonColor="danger"
      description={t(`form.${formKey}.description`, { name: secret.name })}
      title={t(`form.${formKey}.title`)}
      isOpen={isOpen}
      loading={isPending}
      onConfirm={deleteSecretAction}
      onClose={() => onOpenChange(false)}
    />
  );
}
