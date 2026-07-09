// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { Workload } from '@/types/workloads';
import type { ResourceMetrics } from '@/types/projects';

import { Modal } from '@amdenterpriseai/components';
import WorkloadLogs from './WorkloadLogs';

interface Props {
  workload: Workload | ResourceMetrics | undefined;
  onOpenChange: (isOpen: boolean) => void;
  isOpen: boolean;
  /** Project (namespace) the workload belongs to */
  namespace: string;
}

const WorkloadLogsModal = ({
  workload,
  isOpen,
  onOpenChange,
  namespace,
}: Props) => {
  const { t } = useTranslation('workloads');

  const handleClose = () => {
    if (onOpenChange) {
      onOpenChange(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Modal
      onClose={handleClose}
      title={t('list.actions.logs.modal.title')}
      size="5xl"
    >
      <WorkloadLogs workload={workload} isOpen={isOpen} namespace={namespace} />
    </Modal>
  );
};

export default WorkloadLogsModal;
