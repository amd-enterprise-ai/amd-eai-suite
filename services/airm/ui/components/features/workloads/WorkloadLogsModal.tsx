// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { Workload } from '@/types/workloads';

import { Modal } from '@/components/shared/Modal/Modal';
import WorkloadLogs from './WorkloadLogs';
import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  workload: Workload | undefined;
  onOpenChange: (isOpen: boolean) => void;
  isOpen: boolean;
}

const WorkloadLogsModal = ({ workload, isOpen, onOpenChange }: Props) => {
  const { t } = useTranslation('workloads');

  const handleClose = () => {
    if (onOpenChange) {
      onOpenChange(false);
    }
  };

  return (
    <>
      {isOpen && (
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
          <WorkloadLogs workload={workload} isOpen={isOpen} />
        </Modal>
      )}
    </>
  );
};

export default WorkloadLogsModal;
