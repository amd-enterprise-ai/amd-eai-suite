// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { PressEvent, Tooltip } from '@heroui/react';
import { IconRefresh } from '@tabler/icons-react';

import { useTranslation } from 'next-i18next';
import { formatDistance } from 'date-fns';
import { useMemo } from 'react';
import { ActionButton } from '@/components/shared/Buttons';

interface RefreshButtonProps {
  isDisabled?: boolean;
  isLoading?: boolean;
  compact?: boolean;
  lastFetchedTimestamp?: number;
  onPress: (e?: PressEvent) => void;
}

const RefreshButton = ({
  onPress,
  isLoading,
  isDisabled,
  lastFetchedTimestamp,
  compact = true,
}: RefreshButtonProps) => {
  const { t } = useTranslation('common');

  const timeSinceLastUpdate = useMemo(() => {
    if (!lastFetchedTimestamp) return undefined;

    return formatDistance(new Date(), new Date(lastFetchedTimestamp), {
      includeSeconds: true,
    });
  }, [lastFetchedTimestamp]);

  const tooltipContent = useMemo(() => {
    return timeSinceLastUpdate
      ? t(`data.lastUpdated`, { timestamp: timeSinceLastUpdate })
      : t('actions.refresh.title');
  }, [timeSinceLastUpdate, t]);

  const label = isLoading ? t('data.refreshing') : t('data.refresh');

  return (
    <Tooltip
      isDisabled={!timeSinceLastUpdate && !compact}
      content={tooltipContent}
      placement="bottom"
    >
      <ActionButton
        isDisabled={isLoading || isDisabled}
        onPress={onPress}
        aria-label={label}
        size="md"
        icon={<IconRefresh size={16} />}
        isLoading={isLoading}
      >
        {!compact ? label : null}
      </ActionButton>
    </Tooltip>
  );
};

export default RefreshButton;
