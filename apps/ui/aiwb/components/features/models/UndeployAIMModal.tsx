// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useEffect, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { ConfirmationModal } from '@amdenterpriseai/components';

interface ServiceToUndeploy {
  namespace: string;
  serviceId: string;
  displayName: string;
}

interface UndeployAIMModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onConfirmAction: (namespace: string, serviceId: string) => void;
  serviceToUndeploy: ServiceToUndeploy | undefined;
}

export default function UndeployAIMModal({
  isOpen,
  onOpenChange,
  onConfirmAction,
  serviceToUndeploy,
}: UndeployAIMModalProps) {
  const { t } = useTranslation('models', {
    keyPrefix: 'aimCatalog.actions.undeploy',
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setIsLoading(false);
    }
  }, [isOpen]);

  if (!serviceToUndeploy) return null;

  const handleConfirm = () => {
    if (isLoading) return;

    setIsLoading(true);
    onConfirmAction(serviceToUndeploy.namespace, serviceToUndeploy.serviceId);
    onOpenChange(false);
  };

  const handleClose = () => {
    setIsLoading(false);
    onOpenChange(false);
  };

  return (
    <ConfirmationModal
      confirmationButtonColor="danger"
      description={t('confirmation.description', {
        name: serviceToUndeploy.displayName,
      })}
      title={t('confirmation.title')}
      isOpen={isOpen}
      loading={isLoading}
      onConfirm={handleConfirm}
      onClose={handleClose}
    />
  );
}
