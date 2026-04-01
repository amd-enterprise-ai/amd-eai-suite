// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { Workload } from '@amdenterpriseai/types';
import type { ResourceMetrics } from '@/types/namespaces';

import { Modal } from '@amdenterpriseai/components';
import WorkloadLogs, { LogSource } from './WorkloadLogs';

interface Props {
  workload: Workload | ResourceMetrics | undefined;
  onOpenChange: (isOpen: boolean) => void;
  isOpen: boolean;
  /** Log source type - defaults to 'workload' */
  logSource?: LogSource;
  /** Namespace - required when logSource is 'aim' */
  namespace: string;
}

const WorkloadLogsModal = ({
  workload,
  isOpen,
  onOpenChange,
  logSource,
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
      <WorkloadLogs
        workload={workload}
        isOpen={isOpen}
        logSource={logSource}
        namespace={namespace}
      />
    </Modal>
  );
};

export default WorkloadLogsModal;
