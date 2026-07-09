// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ActionButton,
  Card,
  CardFooter,
  CardHeader,
  Divider,
  DropdownActionItem,
  NestedDropdown,
  Status,
  Tooltip,
} from '@amdenterpriseai/components';
import { IconDotsVertical, IconLock } from '@tabler/icons-react';
import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { Intent } from '@amdenterpriseai/types';

import { TruncatedTagsRow } from '@/components/shared/TruncatedTagsRow';

import { AggregatedAIM } from '@/types/aims';

interface CustomModelCardActionHandlers {
  onModelSettings: (aggregatedAim: AggregatedAIM) => void;
  onDelete: (aggregatedAim: AggregatedAIM) => void;
  onDeploy: (aggregatedAim: AggregatedAIM) => void;
}

interface Props extends CustomModelCardActionHandlers {
  aggregatedAim: AggregatedAIM;
}

const CardStatusKind = {
  IMPORTING: 'importing',
  ONBOARDING: 'onboarding',
  FAILED: 'failed',
} as const;
type CardStatusKind = (typeof CardStatusKind)[keyof typeof CardStatusKind];

/**
 * Status pill rendered in the card header, driven directly by the composed
 * onboard phase so it always agrees with the Deploy button:
 * - No pill when the model is `Ready` (the only deployable state).
 * - "Failed" when onboarding failed — including a failed weight import, which
 *   the backend folds into `Failed` even when an AIMProfile exists (profiles
 *   derive from the base image, not the presence of weights in S3).
 * - "Importing" while weights are being downloaded/uploaded to S3.
 * - "Onboarding" for `Pending` (and any model without a composed phase) —
 *   still being prepared or awaiting engine reconciliation.
 */
const resolveCardStatus = (
  aggregatedAim: AggregatedAIM,
): CardStatusKind | null => {
  switch (aggregatedAim.aggregated.onboardPhase) {
    case 'Ready':
      return null;
    case 'Failed':
      return CardStatusKind.FAILED;
    case 'Importing':
      return CardStatusKind.IMPORTING;
    default:
      return CardStatusKind.ONBOARDING;
  }
};

export const CustomModelCard = ({
  aggregatedAim,
  onDeploy,
  onModelSettings,
  onDelete,
}: Props) => {
  const { t } = useTranslation('models');
  const tags = aggregatedAim.aggregated.tags ?? [];
  const isHfTokenRequired = aggregatedAim.aggregated.isHfTokenRequired;

  const cardStatusKind = useMemo(
    () => resolveCardStatus(aggregatedAim),
    [aggregatedAim],
  );

  const cardStatus = useMemo(() => {
    if (cardStatusKind === CardStatusKind.FAILED) {
      return {
        intent: Intent.DANGER,
        label: t('customModels.card.status.failed'),
      };
    }
    if (cardStatusKind === CardStatusKind.IMPORTING) {
      return {
        intent: Intent.PENDING,
        label: t('customModels.card.status.importing'),
      };
    }
    if (cardStatusKind === CardStatusKind.ONBOARDING) {
      return {
        intent: Intent.PENDING,
        label: t('customModels.card.status.onboarding'),
      };
    }
    return null;
  }, [cardStatusKind, t]);

  const isDeployable = aggregatedAim.aggregated.onboardPhase === 'Ready';

  const cardActions = useMemo<DropdownActionItem[]>(
    () => [
      {
        key: 'settings',
        label: t('customModels.card.actions.settings.label'),
        onPress: () => onModelSettings(aggregatedAim),
      },
      {
        key: 'delete',
        label: t('customModels.card.actions.delete.label'),
        color: 'danger',
        onPress: () => onDelete(aggregatedAim),
      },
    ],
    [aggregatedAim, onDelete, onModelSettings, t],
  );

  return (
    <Card
      data-testid="custom-model-card"
      className="flex-1 dark:bg-default-100/50 p-1 grid grid-cols-1 grid-rows-[1fr_auto_auto]"
      shadow="sm"
      radius="md"
      classNames={{
        header: 'flex items-center justify-between min-h-0',
        footer: 'flex flex-nowrap gap-2 justify-between items-center',
      }}
    >
      <CardHeader>
        <div className="flex gap-4 h-full w-full">
          <div className="flex items-start flex-col gap-1 w-full">
            <div className="flex flex-row items-start justify-between w-full gap-2">
              <div className="text-md font-semibold leading-tight">
                {aggregatedAim.aggregated.title}
              </div>
              {cardStatus && (
                <Status
                  label={cardStatus.label}
                  intent={cardStatus.intent}
                  size="sm"
                  isTextColored
                />
              )}
            </div>
            <div className="flex flex-row gap-1 text-sm text-foreground/60">
              <span>{aggregatedAim.aggregated.aiLabName}</span>
              <span>&bull;</span>
              <span>
                {t('aimCatalog.card.versionCount', {
                  count: aggregatedAim.parsedAIMs.length,
                })}
              </span>
              {isHfTokenRequired && (
                <>
                  <span>&bull;</span>
                  <Tooltip
                    content={t('aimCatalog.tooltips.hfTokenRequired')}
                    delay={300}
                  >
                    <span className="cursor-help underline decoration-dotted flex items-center gap-0.5">
                      <IconLock size={12} />
                      {t('aimCatalog.card.gated')}
                    </span>
                  </Tooltip>
                </>
              )}
            </div>
            <p className="text-sm line-clamp-3">
              {aggregatedAim.aggregated.description.short}
            </p>
          </div>
        </div>
      </CardHeader>

      <Divider />
      <CardFooter className="flex flex-row justify-between items-center w-full">
        <TruncatedTagsRow
          tags={tags}
          formatMoreCount={(count) =>
            t('customModels.card.tagsMoreCount', { count })
          }
        />

        <div className="flex flex-row items-center gap-2">
          <NestedDropdown actions={cardActions}>
            <ActionButton
              tertiary
              size="sm"
              aria-label={t('customModels.card.actionsMenu')}
              icon={<IconDotsVertical size={16} />}
              data-testid="custom-model-card-actions"
            />
          </NestedDropdown>
          <ActionButton
            primary
            color="primary"
            size="sm"
            isDisabled={!isDeployable}
            onPress={() => onDeploy(aggregatedAim)}
            data-testid="custom-model-card-deploy"
          >
            {t('aimCatalog.actions.deploy.label')}
          </ActionButton>
        </div>
      </CardFooter>
    </Card>
  );
};

CustomModelCard.displayName = 'CustomModelCard';
