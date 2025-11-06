// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button, ButtonProps } from '@heroui/react';
import { IconX } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';

export const CloseButton = (props: ButtonProps) => {
  const { t } = useTranslation('common');
  return (
    <Button
      {...props}
      data-testid="close-button"
      color="default"
      variant="light"
      radius="full"
      aria-label={t('actions.close.title')}
      isIconOnly
      startContent={<IconX size={20} />}
    />
  );
};
