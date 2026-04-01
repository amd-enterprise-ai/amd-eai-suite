// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { deleteProjectStorage, deleteStorage } from '@/services/app';

import { APIRequestError } from '@amdenterpriseai/utils/app';

import { BaseStorage, Storage } from '@amdenterpriseai/types';

import { ConfirmationModal } from '@amdenterpriseai/components';

interface Props {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  storage: Storage | BaseStorage | null;
  projectId?: string;
}

export const DeleteStorageModal = ({
  isOpen,
  onOpenChange,
  storage,
  projectId,
}: Props) => {
  const { t } = useTranslation('storages');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const formKey = projectId ? 'deleteProjectStorage' : 'delete';
  const { mutate: deleteStorageAction, isPending } = useMutation({
    mutationFn: async () => {
      if (!storage) {
        throw new Error('Storage is null');
      }
      if (projectId) {
        return deleteProjectStorage(projectId, storage.id);
      }
      return deleteStorage(storage.id);
    },
    onSuccess: () => {
      toast.success(t(`form.${formKey}.notification.success`));
      queryClient.invalidateQueries({
        queryKey: projectId ? ['project-storages', projectId] : ['storages'],
      });
      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(
        t(`form.${formKey}.notification.error`),
        error as APIRequestError,
      );
    },
  });

  return (
    <ConfirmationModal
      confirmationButtonColor="danger"
      confirmationButtonText={t(`form.${formKey}.actions.remove.label`)}
      description={t(`form.${formKey}.description`, { name: storage?.name })}
      title={t(`form.${formKey}.title`)}
      isOpen={isOpen}
      loading={isPending}
      onConfirm={deleteStorageAction}
      onClose={() => onOpenChange(false)}
    />
  );
};

export default DeleteStorageModal;
