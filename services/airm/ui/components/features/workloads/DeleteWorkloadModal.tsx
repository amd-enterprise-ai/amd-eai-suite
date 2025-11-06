// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Trans, useTranslation } from 'next-i18next';

import { ProjectWorkloadWithMetrics, Workload } from '@/types/workloads';

import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';

interface DeleteWorkloadModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onConfirmAction: (id: string) => void;
  workload: Workload | ProjectWorkloadWithMetrics | undefined;
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
      description={
        <Trans parent="span">
          {t('list.actions.delete.confirmation.description', {
            name: workload.displayName || '',
          })}
        </Trans>
      }
      title={t('list.actions.delete.confirmation.title')}
      isOpen={isOpen}
      loading={false}
      onConfirm={handleConfirm}
      onClose={() => onOpenChange(false)}
    />
  );
}
