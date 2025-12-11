// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React, { ComponentType, forwardRef, useState } from 'react';

import { Button, Input, InputProps } from '@heroui/react';
import { cn } from '@heroui/react';
import { IconEye, IconEyeOff } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';

interface PasswordInputProps extends InputProps {
  icon?: ComponentType<any>;
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ icon: Icon, startContent, ...props }, ref) => {
    const { t } = useTranslation('common');
    const [reveal, setReveal] = useState(false);

    // If an icon is provided, render it with error-aware styling
    const iconContent = Icon ? (
      <Icon
        className={cn({
          'stroke-danger': props.isInvalid,
          'stroke-neutral-500': !props.isInvalid,
        })}
      />
    ) : null;

    return (
      <Input
        ref={ref}
        labelPlacement="outside"
        variant="bordered"
        {...props}
        type={reveal ? 'text' : 'password'}
        startContent={iconContent || startContent}
        endContent={
          <Button
            variant="light"
            isIconOnly
            size="sm"
            onPress={() => setReveal(!reveal)}
            tabIndex={-1}
            aria-label={
              reveal ? t('password.hidePassword') : t('password.showPassword')
            }
          >
            {reveal ? <IconEyeOff /> : <IconEye />}
          </Button>
        }
      />
    );
  },
);

PasswordInput.displayName = 'PasswordInput';

export default PasswordInput;
