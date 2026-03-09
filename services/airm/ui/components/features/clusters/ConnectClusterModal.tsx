// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Alert, Checkbox, Link, Snippet } from '@heroui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useRef, useState } from 'react';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { addCluster } from '@/services/app/clusters';

import { APIRequestError } from '@/utils/app/errors';

import { CreateClusterResponse } from '@/types/clusters';
import { StepModalHandle } from '@/types/step-modal/step-modal';

import { StepModal } from '@/components/shared/StepModal';
import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  onOpenChange: (isOpen: boolean) => void;
  isOpen: boolean;
}

const ConnectClusterModal: React.FC<Props> = ({ onOpenChange, isOpen }) => {
  const { t } = useTranslation('clusters');
  const [scriptExecuted, setScriptExecuted] = useState<boolean>(false);
  const [connectionParameters, setConnectionParameters] =
    useState<CreateClusterResponse | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();

  const stepModalRef = useRef<StepModalHandle | null>(null);

  const { mutate: createCluster, isPending: isCreatingCluster } = useMutation<
    CreateClusterResponse,
    Error
  >({
    mutationFn: addCluster,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
      setConnectionParameters(data);
      if (stepModalRef?.current) {
        stepModalRef.current.incrementStep();
      }
    },
    onError: (error) => {
      toast.error(t('addCluster.notification.error'), error as APIRequestError);
      console.error('Error creating cluster:', error);
    },
  });

  const handleCreateClusterIdSuccess = useCallback(() => {
    createCluster();
  }, [createCluster]);

  const handleExecutionConfirmation = () => {
    stepModalRef?.current?.setStep(2);
  };

  const handleClose = () => {
    setScriptExecuted(false);
    setConnectionParameters(null);
    stepModalRef?.current?.setStep(0);
    if (onOpenChange) {
      onOpenChange(false);
    }
  };

  const installationCMD = `cluster-id="${connectionParameters?.id}" \
  \ncluster-secret="${connectionParameters?.userSecret}"
  `;

  return (
    <StepModal
      size="2xl"
      isActioning={isCreatingCluster}
      ref={stepModalRef}
      className="min-h-[500px]"
      allowPrevious={false}
      initialStep={0}
      title={t('connectCluster.title')}
      steps={[
        {
          label: t('connectCluster.start.title'),
          content: (
            <Alert
              color="warning"
              className="bg-primary/10!"
              description={t('connectCluster.start.content.description')}
            />
          ),
          customActions: (
            <>
              <ActionButton
                secondary
                isDisabled={isCreatingCluster}
                onPress={handleClose}
              >
                {t('connectCluster.start.actions.cancel')}
              </ActionButton>
              <ActionButton
                primary
                isDisabled={isCreatingCluster}
                onPress={handleCreateClusterIdSuccess}
                isLoading={isCreatingCluster}
              >
                {t('connectCluster.start.actions.next')}
              </ActionButton>
            </>
          ),
        },
        {
          label: t('connectCluster.script.title'),
          content: (
            <div>
              <p>{t('connectCluster.script.content.description')} </p>
              <Snippet
                hideSymbol={true}
                classNames={{
                  base: 'mt-8 w-full',
                  pre: 'whitespace-pre-wrap',
                }}
              >
                <span>{installationCMD}</span>
              </Snippet>

              <Alert
                className="mt-4"
                color="warning"
                title={t('connectCluster.script.content.note')}
              />
              <p className="mt-8">
                <Checkbox
                  aria-label={t('connectCluster.script.content.confirmation')}
                  onValueChange={(value) => {
                    setScriptExecuted(value);
                  }}
                />
                {t('connectCluster.script.content.confirmation')}
              </p>
            </div>
          ),
          customActions: (
            <>
              <ActionButton
                primary
                isDisabled={!scriptExecuted}
                onPress={handleExecutionConfirmation}
              >
                {t('connectCluster.script.actions.next')}
              </ActionButton>
            </>
          ),
          canCloseByOverlayPress: false,
        },
        {
          label: t('connectCluster.final.title'),
          content: (
            <div>
              <p>{t('connectCluster.final.content.description')}</p>
            </div>
          ),
          customActions: (
            <ActionButton primary onPress={handleClose}>
              {t('connectCluster.final.actions.complete')}
            </ActionButton>
          ),
        },
      ]}
      onOpenChange={onOpenChange}
      onCancel={handleClose}
      isOpen={isOpen}
    />
  );
};

export default ConnectClusterModal;
