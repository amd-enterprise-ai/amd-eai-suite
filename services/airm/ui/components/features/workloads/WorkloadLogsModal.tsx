// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { Workload } from '@/types/workloads';

import { Modal } from '@/components/shared/Modal/Modal';
import WorkloadLogs from './WorkloadLogs';
import { ActionButton } from '@/components/shared/Buttons';
import { useState, useEffect } from 'react';

interface Props {
  workload: Workload | undefined;
  onOpenChange: (isOpen: boolean) => void;
  isOpen: boolean;
}

const WorkloadLogsModal = ({ workload, isOpen, onOpenChange }: Props) => {
  const { t } = useTranslation('workloads');
  const [isModalOpen, setIsModalOpen] = useState(isOpen);

  // Sync internal state with prop changes
  useEffect(() => {
    setIsModalOpen(isOpen);
  }, [isOpen]);

  const handleClose = () => {
    if (onOpenChange) {
      setIsModalOpen(false);

      // this is implemented this way to let cleanup operations finish before unmounting the modal
      setTimeout(() => {
        onOpenChange(false);
      }, 300);
    }
  };

  // Only render when modal should be open
  if (!isOpen) {
    return null;
  }

  return (
    <Modal
      onClose={handleClose}
      title={t('list.actions.logs.modal.title')}
      size="3xl"
      footer={
        <ActionButton primary onPress={handleClose}>
          {t('actions.close.title', { ns: 'common' })}
        </ActionButton>
      }
    >
      <WorkloadLogs workload={workload} isOpen={isModalOpen} />
    </Modal>
  );
};

export default WorkloadLogsModal;
