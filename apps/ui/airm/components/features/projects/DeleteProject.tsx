// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import React, { useCallback } from 'react';

import { useTranslation } from 'next-i18next';
import router from 'next/router';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { deleteProject as deleteProjectAPI } from '@/services/app';

import { APIRequestError } from '@amdenterpriseai/utils/app';

import { Project } from '@amdenterpriseai/types';

import { ConfirmationModal } from '@amdenterpriseai/components';
import { ActionButton } from '@amdenterpriseai/components';

const translationSet = 'projects';

interface Props {
  project: Project;
}

export const DeleteProject: React.FC<Props> = ({ project }) => {
  const { t } = useTranslation(translationSet);
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();
  const { isOpen, onOpen, onOpenChange } = useDisclosure();
  const { mutate: deleteProject, isPending } = useMutation({
    mutationFn: deleteProjectAPI,
    onSuccess: () => {
      onOpenChange();
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success(t('settings.delete.notification.success'));

      router.push('/projects');
    },
    onError: (error) => {
      toast.error(
        t('settings.delete.notification.error'),
        error as APIRequestError,
      );
      onOpenChange();
    },
  });

  const handleDelete = useCallback(() => {
    // Delete project
    deleteProject(project.id);
  }, [deleteProject, project]);

  return (
    <>
      <div className="rounded-sm flex flex-col">
        <p>{t('settings.delete.message')}</p>
        <ActionButton
          primary
          aria-label={t('settings.delete.action') || ''}
          className="mt-6 max-w-48"
          color="danger"
          size="sm"
          onPress={onOpen}
          icon={<IconAlertTriangle size={16} />}
        >
          {t('settings.delete.action')}
        </ActionButton>
      </div>
      <ConfirmationModal
        confirmationButtonColor="danger"
        description={t('settings.delete.confirmation.description', {
          project: project.name,
        })}
        title={t('settings.delete.confirmation.title')}
        isOpen={isOpen}
        loading={isPending}
        onConfirm={handleDelete}
        onClose={onOpenChange}
      />
    </>
  );
};

export default DeleteProject;
