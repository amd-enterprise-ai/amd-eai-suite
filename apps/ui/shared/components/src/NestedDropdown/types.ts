// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ReactNode } from 'react';

import { ActionFieldHintType } from '@amdenterpriseai/types';

export type DropdownItemHint = {
  type: ActionFieldHintType;
  message: string;
};

export type DropdownItem = {
  key: string;
  className?: string;
  onPress: () => void;
  startContent?: ReactNode;
  color?: string;
  label: string;
  hint?: DropdownItemHint[];
  isDisabled?: boolean;
  description?: string | ReactNode;
  actions?: DropdownItem[];
  isSection?: boolean;
};
