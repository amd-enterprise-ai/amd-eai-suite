// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Card, CardFooter, CardHeader, Chip, Divider } from '@heroui/react';
import { IconExternalLink } from '@tabler/icons-react';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { CatalogItem } from '@/types/catalog';
import { Color } from '@/types/colors';
import { ActionItem } from '@/types/data-table/clientside-table';

import { ActionButton } from '@/components/shared/Buttons';
import ThreeDotActionsDropdown from '@/components/shared/Dropdown/ThreeDotActionsDropdown';

interface Props {
  cardActions?: ActionItem<any>[];
  isDeployed?: boolean;
  isPending?: boolean;
  item: CatalogItem;
  primaryAction?: ActionItem<any>;
  secondaryAction?: ActionItem<any>;
  secondaryActionColor?: Color;
  pendingLabel: string;
  readyAction?: ActionItem<any>;
  iconComponent?: React.ReactNode;
  minHeaderHeight?: string;
  iconTopGap?: boolean;
}

export const CatalogItemCard = ({
  cardActions,
  isDeployed,
  isPending,
  item,
  primaryAction,
  secondaryAction,
  secondaryActionColor,
  pendingLabel,
  readyAction,
  iconComponent,
  minHeaderHeight,
  iconTopGap,
}: Props) => {
  const { t } = useTranslation('catalog');

  const finalCardActions = useMemo(
    () =>
      cardActions
        ? [
            {
              key: 'view',
              label: t('list.actions.view'),
              onPress: () => {
                if (item.externalUrl) {
                  window.open(item.externalUrl, '_blank');
                }
              },
              isDisabled: !item.externalUrl,
              startContent: <IconExternalLink />,
            },
            ...cardActions,
          ]
        : null,
    [cardActions, t, item.externalUrl],
  );

  return (
    <Card
      className="max-w-[450px] min-w-[380px] flex-1 dark:bg-default-100/50 p-1"
      key={item.id}
      shadow="sm"
      radius="md"
      isDisabled={!item.available}
      classNames={{
        header: `flex items-center justify-between`,
        footer: `flex flex-nowrap gap-2 justify-between items-start`,
      }}
    >
      <CardHeader>
        <div
          className="flex gap-4 h-full"
          style={{ minHeight: minHeaderHeight }} // style override as tailwind does not work with dynamic min-h-* classes
        >
          <div className={iconTopGap ? 'mt-1' : ''}>{iconComponent}</div>
          <div className="flex items-start flex-col">
            <div className="text-md font-semibold">
              {item.displayName ?? item.name}
            </div>
            <p className="mt-2 text-sm">{item.description}</p>
          </div>
        </div>
        <div>
          {finalCardActions ? (
            <ThreeDotActionsDropdown actions={finalCardActions} item={item} />
          ) : (
            <ActionButton
              tertiary
              color="primary"
              onPress={() => {
                if (item.externalUrl) {
                  window.open(item.externalUrl, '_blank');
                }
              }}
              isDisabled={!item.externalUrl}
              icon={<IconExternalLink />}
            />
          )}
        </div>
      </CardHeader>
      <Divider />
      <CardFooter>
        <div className="flex flex-wrap gap-2">
          {item.tags?.map((tag) => (
            <Chip key={tag} variant="bordered" size="sm">
              {tag}
            </Chip>
          ))}
        </div>
        <div className="flex gap-2">
          {secondaryAction ? (
            <ActionButton
              size="sm"
              color={secondaryActionColor ?? 'primary'}
              onPress={() => secondaryAction.onPress(item)}
              isDisabled={!item.available}
            >
              {secondaryAction.label}
            </ActionButton>
          ) : null}
          {!isDeployed && !isPending && primaryAction ? (
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
      </CardFooter>
    </Card>
  );
};

CatalogItemCard.displayName = 'CatalogItemCard';
