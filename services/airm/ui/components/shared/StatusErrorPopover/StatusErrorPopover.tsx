// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button, Popover, PopoverContent, PopoverTrigger } from '@heroui/react';
import { IconChevronLeft, IconChevronRight } from '@tabler/icons-react';
import { useState } from 'react';

import { useTranslation } from 'next-i18next';

import { SecondaryStatusReason } from '@/types/status-error-popover';

interface Props {
  statusReason: string | null;
  secondaryStatusReasons?: SecondaryStatusReason[];
  triggerText: string;
  headerText: string;
}

export const StatusErrorPopover: React.FC<Props> = ({
  statusReason,
  secondaryStatusReasons,
  triggerText,
  headerText,
}) => {
  const [currentReason, setCurrentReason] =
    useState<SecondaryStatusReason | null>(
      secondaryStatusReasons && secondaryStatusReasons.length > 0
        ? secondaryStatusReasons[0]
        : null,
    );
  const { t } = useTranslation('common');
  const [currentIndex, setCurrentIndex] = useState(0);

  return (
    <Popover placement="bottom">
      <PopoverTrigger>
        <span className="text-sm underline">({triggerText})</span>
      </PopoverTrigger>
      <PopoverContent>
        <div className="px-1 py-2 max-w-[400px] flex flex-col gap-2">
          <div>{headerText}</div>

          {!!statusReason ? (
            <div className="text-sm bg-default-200 my-2 p-1 whitespace-pre-line">
              <code>{statusReason}</code>
            </div>
          ) : null}

          {secondaryStatusReasons && secondaryStatusReasons.length > 0 && (
            <>
              <strong>{t('status.errorDetail.title')}</strong>

              {currentReason ? (
                <>
                  <span>{currentReason.key}</span>
                  <div className="text-sm bg-default-200 my-1 p-1 whitespace-pre-line">
                    <code>{currentReason.description}</code>
                  </div>
                </>
              ) : null}
              <div className="flex items-center gap-2 justify-center">
                <Button
                  size="sm"
                  isIconOnly
                  isDisabled={currentIndex === 0}
                  aria-label={t('status.errorDetail.action.prev')}
                  onPress={() => {
                    setCurrentIndex((prev) => {
                      const newIndex = prev - 1;
                      setCurrentReason(secondaryStatusReasons[newIndex]);
                      return newIndex;
                    });
                  }}
                >
                  <IconChevronLeft size={16} />
                </Button>
                <span>
                  {currentIndex + 1} / {secondaryStatusReasons.length}
                </span>
                <Button
                  size="sm"
                  isIconOnly
                  isDisabled={
                    currentIndex === secondaryStatusReasons.length - 1
                  }
                  aria-label={t('status.errorDetail.action.next')}
                  onPress={() => {
                    setCurrentIndex((prev) => {
                      const newIndex = prev + 1;
                      setCurrentReason(secondaryStatusReasons[newIndex]);
                      return newIndex;
                    });
                  }}
                >
                  <IconChevronRight size={16} />
                </Button>
              </div>
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
};

export default StatusErrorPopover;
