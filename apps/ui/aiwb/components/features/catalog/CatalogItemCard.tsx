// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Card, CardFooter, CardHeader, Chip, Divider } from '@heroui/react';
import { IconExternalLink, IconTrash } from '@tabler/icons-react';

import { TruncatedTagsRow } from '@/components/shared/TruncatedTagsRow';

import { useTranslation } from 'next-i18next';

import { CatalogItem } from '@amdenterpriseai/types';
import { Color } from '@amdenterpriseai/types';
import { ActionItem } from '@amdenterpriseai/types';

import { ActionButton } from '@amdenterpriseai/components';

interface Props {
  isDeployed?: boolean;
  isPending?: boolean;
  isFailed?: boolean;
  item: CatalogItem;
  primaryAction?: ActionItem<any>;
  secondaryAction?: ActionItem<any>;
  secondaryActionColor?: Color;
  pendingLabel: string;
  readyAction?: ActionItem<any>;
  iconComponent?: React.ReactNode;
  minHeaderHeight?: string;
  iconTopGap?: boolean;
  onOpenWorkloadDetails?: (workloadId: string) => void;
}

export const CatalogItemCard = ({
  isDeployed,
  isPending,
  isFailed,
  item,
  primaryAction,
  secondaryAction,
  secondaryActionColor,
  pendingLabel,
  readyAction,
  iconComponent,
  minHeaderHeight,
  iconTopGap,
  onOpenWorkloadDetails,
}: Props) => {
  const { t } = useTranslation('catalog');

  return (
    <Card
      className="w-full min-w-0 dark:bg-default-100/50 p-1"
      key={item.id}
      shadow="sm"
      radius="md"
      isDisabled={!item.available}
      classNames={{
        header: `flex items-start justify-between`,
        footer: `flex flex-nowrap gap-2 justify-between items-start`,
      }}
    >
      <CardHeader>
        <div
          className="flex gap-4 h-full"
          style={{ minHeight: minHeaderHeight }} // style override as tailwind does not work with dynamic min-h-* classes
        >
          <div className={iconTopGap ? 'mt-1' : ''}>{iconComponent}</div>
          <div className="flex items-start flex-col flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-md font-semibold">
                {item.displayName ?? item.name}
              </span>
              {isFailed && (
                <Chip size="sm" color="danger" variant="flat">
                  {t('status.Failed')}
                </Chip>
              )}
            </div>
            <div className="mt-2 text-sm flex flex-col gap-0">
              <p className="min-w-0">{item.description}</p>
              {item.externalUrl && (
                <span className="flex items-center gap-1 mt-1">
                  <button
                    type="button"
                    onClick={() => window.open(item.externalUrl!, '_blank')}
                    className="text-primary inline-flex items-center gap-1 hover:underline focus:outline-none focus:underline"
                  >
                    <span>{t('card.moreInformation')}</span>
                    <IconExternalLink size={14} />
                  </button>
                </span>
              )}
            </div>
          </div>
        </div>
      </CardHeader>
      <Divider />
      <CardFooter>
        <div className="flex flex-row justify-between items-center w-full gap-2">
          <div className="min-w-0 overflow-hidden">
            <TruncatedTagsRow
              tags={item.tags ?? []}
              formatMoreCount={(count) => t('card.tagsMoreCount', { count })}
            />
          </div>
          <div className="flex gap-2 shrink-0">
            {onOpenWorkloadDetails && item.workloads?.[0]?.id ? (
              <ActionButton
                secondary
                size="sm"
                color="default"
                onPress={() => onOpenWorkloadDetails(item.workloads![0].id)}
              >
                {t('list.actions.details')}
              </ActionButton>
            ) : null}
            {secondaryAction ? (
              <ActionButton
                size="sm"
                color={secondaryActionColor ?? 'primary'}
                onPress={() => secondaryAction.onPress(item)}
                isDisabled={!item.available}
                startContent={isFailed ? <IconTrash size={16} /> : undefined}
              >
                {secondaryAction.label}
              </ActionButton>
            ) : null}
            {!isDeployed && !isPending && !isFailed && primaryAction ? (
              <ActionButton
                primary
                size="sm"
                onPress={() => primaryAction.onPress(item)}
                isDisabled={!item.available}
              >
                {primaryAction.label}
              </ActionButton>
            ) : null}
            {isPending ? (
              <ActionButton size="sm" isLoading>
                {pendingLabel}
              </ActionButton>
            ) : null}
            {!isPending && isDeployed && readyAction ? (
              <ActionButton
                primary
                size="sm"
                color="secondary"
                onPress={() => readyAction.onPress(item)}
              >
                {readyAction.label}
              </ActionButton>
            ) : null}
          </div>
        </div>
      </CardFooter>
    </Card>
  );
};

CatalogItemCard.displayName = 'CatalogItemCard';
