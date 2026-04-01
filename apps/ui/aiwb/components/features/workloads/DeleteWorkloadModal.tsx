// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { Workload } from '@amdenterpriseai/types';
import type { ResourceMetrics } from '@/types/namespaces';

import { ConfirmationModal } from '@amdenterpriseai/components';

interface DeleteWorkloadModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onConfirmAction: (id: string) => void;
  workload: Workload | ResourceMetrics | undefined;
}

export default function DeleteWorkloadModal({
  isOpen,
  onOpenChange,
  onConfirmAction,
  workload,
}: DeleteWorkloadModalProps) {
  const { t } = useTranslation('workloads');

  if (!workload) return null;

  const handleConfirm = () => {
    onConfirmAction(workload.id);
    onOpenChange(false);
  };

  return (
    <ConfirmationModal
      confirmationButtonColor="danger"
      description={t('list.actions.delete.confirmation.description', {
        name: workload.displayName || '',
      })}
      title={t('list.actions.delete.confirmation.title')}
      isOpen={isOpen}
      loading={false}
      onConfirm={handleConfirm}
      onClose={() => onOpenChange(false)}
    />
  );
}
