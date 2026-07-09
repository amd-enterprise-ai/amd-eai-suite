// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { ActionFieldHintType } from '@amdenterpriseai/types';

import {
  NestedDropdown,
  type DropdownActionItem,
} from '../../../src/NestedDropdown';

export default {
  title: 'Components/NestedDropdown',
} satisfies StoryDefault;

const noop = () => {};

const mixedActions: DropdownActionItem[] = [
  {
    key: 'connect',
    label: 'Connect',
    description: 'Open connection settings',
    onPress: noop,
  },
  {
    key: 'manage',
    label: 'Manage deployment',
    onPress: noop,
    actions: [
      {
        key: 'resources',
        label: 'Change resources',
        onPress: noop,
        actions: [
          { key: 'scale-up', label: 'Scale up', onPress: noop },
          { key: 'scale-down', label: 'Scale down', onPress: noop },
        ],
      },
      { key: 'restart', label: 'Restart', onPress: noop },
      {
        key: 'undeploy',
        label: 'Undeploy',
        color: 'danger',
        onPress: noop,
      },
    ],
  },
  {
    key: 'more',
    label: 'More actions',
    onPress: noop,
    actions: [
      { key: 'duplicate', label: 'Duplicate', onPress: noop },
      {
        key: 'archive',
        label: 'Archive',
        isDisabled: true,
        onPress: noop,
      },
    ],
  },
  {
    key: 'delete',
    label: 'Delete',
    color: 'danger',
    isDisabled: true,
    hint: [
      {
        message: 'Cannot delete while deployment is running',
        type: ActionFieldHintType.WARNING,
      },
    ],
    onPress: noop,
  },
];

export const Mixed: Story = () => (
  <div className="p-8">
    <NestedDropdown actions={mixedActions} />
  </div>
);
