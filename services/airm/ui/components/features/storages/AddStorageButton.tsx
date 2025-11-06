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

import { AddStorageButtonOptions } from '@/types/storages';

import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  inProject?: boolean;
  storageTypes: AddStorageButtonOptions;
  disabled?: boolean;
}

const AddStorageButton: React.FC<Props> = ({
  storageTypes,
  disabled,
  inProject = false,
}) => {
  const { t } = useTranslation('storages');
  const label = t(
    inProject ? 'actions.addProjectStorage.label' : 'actions.add.label',
  );

  return (
    <Dropdown isDisabled={disabled}>
      <DropdownTrigger>
        <ActionButton primary aria-label={label} isDisabled={disabled}>
          {label}
        </ActionButton>
      </DropdownTrigger>

      <DropdownMenu>
        {Object.entries(storageTypes).map(([key, handler]) => (
          <DropdownItem onPress={handler} key={`add-storage-${key}`}>
            {t(`actions.add.options.${key}.label`)}
          </DropdownItem>
        ))}
      </DropdownMenu>
    </Dropdown>
  );
};

export default AddStorageButton;
