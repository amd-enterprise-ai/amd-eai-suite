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

import { ActionButton } from '@amdenterpriseai/components';
import { useAccessControl } from '@/hooks/useAccessControl';
import { IconChevronDown } from '@tabler/icons-react';

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
  const { isAdministrator } = useAccessControl();
  const triggerLabel = t('actions.addProjectSecret.label');
  return (
    <Dropdown isDisabled={disabled}>
      <DropdownTrigger>
        <ActionButton
          primary
          aria-label={triggerLabel}
          isDisabled={disabled}
          endContent={<IconChevronDown size={16} stroke={2} />}
        >
          {triggerLabel}
        </ActionButton>
      </DropdownTrigger>

      <DropdownMenu
        disabledKeys={!isAdministrator ? ['add-project-assignment'] : []}
      >
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
