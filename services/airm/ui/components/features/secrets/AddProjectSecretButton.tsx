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

import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  inProject?: boolean;
  disabled?: boolean;
  onOpenProjectSecret: () => void;
  onOpenProjectAssignment: () => void;
}

const AddProjectSecretButton: React.FC<Props> = ({
  disabled,
  onOpenProjectSecret,
  onOpenProjectAssignment,
}) => {
  const { t } = useTranslation('secrets');

  const triggerLabel = t('actions.addProjectSecret.label');
  return (
    <Dropdown isDisabled={disabled}>
      <DropdownTrigger>
        <ActionButton primary aria-label={triggerLabel} isDisabled={disabled}>
          {triggerLabel}
        </ActionButton>
      </DropdownTrigger>

      <DropdownMenu>
        <DropdownItem onPress={onOpenProjectSecret} key={`add-project-secret`}>
          {t(`actions.addProjectSecret.options.add.label`)}
        </DropdownItem>
        <DropdownItem
          onPress={onOpenProjectAssignment}
          key={`add-project-assignment`}
        >
          {t(`actions.addProjectSecret.options.assign.label`)}
        </DropdownItem>
      </DropdownMenu>
    </Dropdown>
  );
};

export default AddProjectSecretButton;
