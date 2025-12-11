// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
} from '@heroui/react';
import React from 'react';

import { useTranslation } from 'next-i18next';

import { StorageType } from '@/types/enums/storages';

import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  onAssignS3Storage: () => void;
  disabled?: boolean;
}

export const AssignStorageButton: React.FC<Props> = ({
  onAssignS3Storage,
  disabled,
}) => {
  const { t } = useTranslation('storages');
  const label = t('actions.assignStorage.label');

  return (
    <Dropdown isDisabled={disabled}>
      <DropdownTrigger>
        <ActionButton primary aria-label={label} isDisabled={disabled}>
          {label}
        </ActionButton>
      </DropdownTrigger>

      <DropdownMenu>
        <DropdownItem onPress={onAssignS3Storage} key="assign-storage-S3">
          {t(`actions.assignStorage.options.${StorageType.S3}.label`)}
        </DropdownItem>
      </DropdownMenu>
    </Dropdown>
  );
};

export default AssignStorageButton;
