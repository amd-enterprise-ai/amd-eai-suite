// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { deleteProjectStorage, deleteStorage } from '@/services/app/storages';

import { APIRequestError } from '@/utils/app/errors';

import { BaseStorage, Storage } from '@/types/storages';

import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';

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
