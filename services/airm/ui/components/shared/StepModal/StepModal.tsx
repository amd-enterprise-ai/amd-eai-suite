// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  cn,
} from '@heroui/react';
import { useCallback, useState } from 'react';
import { forwardRef, useImperativeHandle } from 'react';

import { useTranslation } from 'next-i18next';

import { StepModalHandle, StepModalStep } from '@/types/step-modal/step-modal';
import { CloseButton, ActionButton } from '@/components/shared/Buttons';
import Stepper from '../Stepper/Stepper';

interface Props {
  className?: string;
  initialStep: number;
  steps: StepModalStep[];
  allowPrevious?: boolean;
  onOpenChange: (isOpen: boolean) => void;
  isOpen: boolean;
  onCancel?: () => void;
  isActioning?: boolean;
  resetOnClose?: boolean;
  title?: string;
  size?:
    | '2xl'
    | 'sm'
    | 'md'
    | 'lg'
    | 'xl'
    | 'full'
    | 'xs'
    | '3xl'
    | '4xl'
    | '5xl';
}

export const StepModal = forwardRef<StepModalHandle, Props>(
  (
    {
      className,
      allowPrevious,
      initialStep = 0,
      steps,
      isOpen,
      onOpenChange,
      onCancel,
      size,
      isActioning,
      title,
      resetOnClose = true,
    },
    ref,
  ) => {
    const { t } = useTranslation('common');
    const [currentStep, setCurrentStep] = useState<number>(initialStep || 0);

    useImperativeHandle(
      ref,
      () => ({
        incrementStep: () => {
          setCurrentStep((prev) =>
            prev + 1 > steps.length - 1 ? steps.length - 1 : prev + 1,
          );
        },
        setStep: (step: number) => {
          setCurrentStep(step);
        },
      }),
      [steps.length],
    );

    const handleNext = useCallback(() => {
      if (steps) {
        const step = steps[currentStep];
        if (step.onStepChange) {
          step.onStepChange(currentStep + 1);
          return;
        }
      }
      setCurrentStep((prev) => prev + 1);
    }, [currentStep, steps]);

    const handlePrev = useCallback(() => {
      if (steps) {
        const step = steps[currentStep];
        if (step.onStepChange) {
          step.onStepChange(currentStep - 1);
          return;
        }
      }
      setCurrentStep((prev) => prev - 1);
    }, [currentStep, steps]);

    const handleClose = useCallback(() => {
      if (resetOnClose) {
        setCurrentStep(0);
      }
      if (onCancel) {
        onCancel();
      }
    }, [resetOnClose, onCancel]);

    return (
      <Modal
        isOpen={isOpen}
        size={size}
        onOpenChange={onOpenChange}
        classNames={{
          base: cn('overflow-y-auto overflow-x-hidden', className),
          header: 'border-b-1 border-default-200 w-full pr-[64px]',
          body: 'py-6',
          closeButton: 'top-2.5 right-2.5',
          footer: 'justify-center w-full',
        }}
        onClose={handleClose}
        closeButton={<CloseButton />}
        hideCloseButton={isActioning}
        isDismissable={
          !isActioning &&
          (typeof steps[currentStep]?.canCloseByOverlayPress === 'undefined' ||
            steps[currentStep]?.canCloseByOverlayPress)
        }
      >
        <ModalContent>
          <ModalHeader>{title ?? steps?.[currentStep].label}</ModalHeader>
          <ModalBody className="w-full">
            <div className="mx-auto w-5/6">
              <Stepper
                step={currentStep}
                steps={steps.map((step) => ({ label: step.label }))}
              />
            </div>
            {steps?.[currentStep].content}
          </ModalBody>
          <ModalFooter>
            {steps?.[currentStep]?.customActions ? (
              steps?.[currentStep]?.customActions
            ) : (
              <div className={'flex items-center gap-2'}>
                {currentStep > 0 &&
                allowPrevious &&
                !steps?.[currentStep]?.hidePrev ? (
                  <ActionButton
                    secondary
                    aria-label={
                      steps?.[currentStep]?.backActionLabel ||
                      t('actions.previous') ||
                      ''
                    }
                    onPress={handlePrev}
                  >
                    {steps?.[currentStep]?.backActionLabel ||
                      t('actions.previous')}
                  </ActionButton>
                ) : null}
                {currentStep < steps.length - 1 &&
                !steps?.[currentStep]?.hideNext ? (
                  <ActionButton
                    primary
                    isLoading={isActioning}
                    aria-label={
                      steps?.[currentStep].nextActionLabel ||
                      t('actions.next') ||
                      ''
                    }
                    type="submit"
                    onPress={handleNext}
                  >
                    {steps?.[currentStep].nextActionLabel || t('actions.next')}
                  </ActionButton>
                ) : null}
              </div>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>
    );
  },
);

StepModal.displayName = 'StepModal';

export default StepModal;
