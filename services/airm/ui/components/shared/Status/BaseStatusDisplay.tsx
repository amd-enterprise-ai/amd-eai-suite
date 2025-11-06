// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { JSX } from 'react';

import { useTranslation } from 'next-i18next';

import { SecondaryStatusReason } from '@/types/status-error-popover';

import { StatusErrorPopover } from '@/components/shared/StatusErrorPopover';

interface Props<T extends string | number | symbol> {
  status: T;
  statusPrefix: string;
  translationNamespace: string;
  statusReason: string | null;
  secondaryStatusReason?: SecondaryStatusReason[];
  statusIconMap: Record<T, JSX.Element | null>;
  statusesToHide?: T[];
  hasErrors: boolean;
}

export const BaseStatusDisplay = <T extends string | number | symbol>({
  status,
  statusPrefix,
  translationNamespace,
  statusReason,
  secondaryStatusReason,
  statusIconMap,
  statusesToHide,
  hasErrors,
}: Props<T>) => {
  const { t } = useTranslation(translationNamespace);

  return (
    <span className="inline-flex items-center gap-1 text-sm font-medium">
      {statusIconMap[status]}
      {!statusesToHide?.some((s) => s === status)
        ? t(`${statusPrefix}.${String(status)}`)
        : null}
      {hasErrors && (!!statusReason || secondaryStatusReason) && (
        <StatusErrorPopover
          statusReason={statusReason}
          secondaryStatusReasons={secondaryStatusReason}
          triggerText={t('statusReason.messageTrigger')}
          headerText={t('statusReason.messageHeader')}
        />
      )}
    </span>
  );
};

export default BaseStatusDisplay;
