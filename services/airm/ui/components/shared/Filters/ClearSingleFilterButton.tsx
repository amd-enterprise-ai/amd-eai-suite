// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button, PressEvent } from '@heroui/react';
import { IconX } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';
import React from 'react';

const ClearSingleFilterButton: React.FC<{
  onPress: (e: PressEvent) => void;
}> = ({ onPress }) => {
  const { t } = useTranslation('common');
  return (
    <Button
      onPress={onPress}
      radius="full"
      isIconOnly
      variant="light"
      aria-label={t('actions.clear.title')}
      className="absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 min-w-6 text-foreground z-10"
      tabIndex={0}
    >
      <IconX size={16} stroke={2} />
    </Button>
  );
};

export default ClearSingleFilterButton;
