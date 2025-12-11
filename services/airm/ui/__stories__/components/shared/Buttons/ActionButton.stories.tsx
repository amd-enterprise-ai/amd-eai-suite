// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { ActionButton } from '@/components/shared/Buttons/ActionButton';
import {
  IconPlus,
  IconSettings,
  IconTrash,
  IconEdit,
  IconCheck,
  IconX,
  IconSend,
} from '@tabler/icons-react';

export default {
  title: 'Components/Shared/Buttons/ActionButton',
} satisfies StoryDefault;

// ============================================================================
// Basic Variants
// ============================================================================

export const Primary: Story = () => (
  <ActionButton primary onPress={() => alert('Primary clicked!')}>
    Save Changes
  </ActionButton>
);

export const Secondary: Story = () => (
  <ActionButton secondary onPress={() => alert('Secondary clicked!')}>
    Cancel
  </ActionButton>
);

export const Tertiary: Story = () => (
  <ActionButton tertiary onPress={() => alert('Tertiary clicked!')}>
    Learn More
  </ActionButton>
);

export const AllVariants: Story = () => (
  <div className="flex gap-4 items-center">
    <ActionButton primary>Primary</ActionButton>
    <ActionButton secondary>Secondary</ActionButton>
    <ActionButton tertiary>Tertiary</ActionButton>
  </div>
);

// ============================================================================
// With Icons
// ============================================================================

export const WithIcons: Story = () => (
  <div className="flex gap-4 items-center">
    <ActionButton primary icon={<IconPlus size={18} />}>
      Add Item
    </ActionButton>
    <ActionButton secondary icon={<IconSettings size={18} />}>
      Settings
    </ActionButton>
    <ActionButton tertiary icon={<IconEdit size={18} />}>
      Edit
    </ActionButton>
  </div>
);

export const IconOnly: Story = () => (
  <div className="flex gap-4 items-center">
    <ActionButton primary icon={<IconPlus size={18} />} aria-label="Add" />
    <ActionButton
      secondary
      icon={<IconSettings size={18} />}
      aria-label="Settings"
    />
    <ActionButton tertiary icon={<IconTrash size={18} />} aria-label="Delete" />
  </div>
);

// ============================================================================
// Sizes
// ============================================================================

export const Sizes: Story = () => (
  <div className="flex flex-col gap-6">
    <div className="flex gap-4 items-center">
      <ActionButton primary size="sm">
        Small
      </ActionButton>
      <ActionButton primary size="md">
        Medium
      </ActionButton>
      <ActionButton primary size="lg">
        Large
      </ActionButton>
    </div>
    <div className="flex gap-4 items-center">
      <ActionButton secondary size="sm">
        Small
      </ActionButton>
      <ActionButton secondary size="md">
        Medium
      </ActionButton>
      <ActionButton secondary size="lg">
        Large
      </ActionButton>
    </div>
    <div className="flex gap-4 items-center">
      <ActionButton tertiary size="sm">
        Small
      </ActionButton>
      <ActionButton tertiary size="md">
        Medium
      </ActionButton>
      <ActionButton tertiary size="lg">
        Large
      </ActionButton>
    </div>
  </div>
);

export const IconOnlySizes: Story = () => (
  <div className="flex gap-4 items-center">
    <ActionButton
      primary
      size="sm"
      icon={<IconPlus size={14} />}
      aria-label="Add small"
    />
    <ActionButton
      primary
      size="md"
      icon={<IconPlus size={18} />}
      aria-label="Add medium"
    />
    <ActionButton
      primary
      size="lg"
      icon={<IconPlus size={22} />}
      aria-label="Add large"
    />
  </div>
);

// ============================================================================
// Colors
// ============================================================================

export const PrimaryColors: Story = () => (
  <div className="flex gap-4 items-center flex-wrap">
    <ActionButton primary color="primary">
      Primary
    </ActionButton>
    <ActionButton primary color="secondary">
      Secondary
    </ActionButton>
    <ActionButton primary color="success">
      Success
    </ActionButton>
    <ActionButton primary color="warning">
      Warning
    </ActionButton>
    <ActionButton primary color="danger">
      Danger
    </ActionButton>
    <ActionButton primary color="default">
      Default
    </ActionButton>
  </div>
);

export const SecondaryColors: Story = () => (
  <div className="flex gap-4 items-center flex-wrap">
    <ActionButton secondary color="primary">
      Primary
    </ActionButton>
    <ActionButton secondary color="secondary">
      Secondary
    </ActionButton>
    <ActionButton secondary color="success">
      Success
    </ActionButton>
    <ActionButton secondary color="warning">
      Warning
    </ActionButton>
    <ActionButton secondary color="danger">
      Danger
    </ActionButton>
    <ActionButton secondary color="default">
      Default
    </ActionButton>
  </div>
);

export const TertiaryColors: Story = () => (
  <div className="flex gap-4 items-center flex-wrap">
    <ActionButton tertiary color="primary">
      Primary
    </ActionButton>
    <ActionButton tertiary color="secondary">
      Secondary
    </ActionButton>
    <ActionButton tertiary color="success">
      Success
    </ActionButton>
    <ActionButton tertiary color="warning">
      Warning
    </ActionButton>
    <ActionButton tertiary color="danger">
      Danger
    </ActionButton>
    <ActionButton tertiary color="default">
      Default
    </ActionButton>
  </div>
);

// ============================================================================
// States
// ============================================================================

export const Loading: Story = () => (
  <div className="flex flex-col gap-4">
    <div className="flex gap-4 items-center">
      <ActionButton primary isLoading>
        Saving...
      </ActionButton>
      <ActionButton secondary isLoading>
        Loading
      </ActionButton>
      <ActionButton tertiary isLoading>
        Processing
      </ActionButton>
    </div>
    <div className="flex gap-4 items-center">
      <ActionButton primary icon={<IconCheck size={18} />} isLoading>
        Confirming...
      </ActionButton>
      <ActionButton secondary icon={<IconSettings size={18} />} isLoading>
        Updating
      </ActionButton>
    </div>
    <div className="flex gap-4 items-center">
      <ActionButton
        primary
        icon={<IconPlus size={18} />}
        isLoading
        aria-label="Adding"
      />
      <ActionButton
        secondary
        icon={<IconSettings size={18} />}
        isLoading
        aria-label="Loading settings"
      />
      <ActionButton
        tertiary
        icon={<IconTrash size={18} />}
        isLoading
        aria-label="Deleting"
      />
    </div>
  </div>
);

export const Disabled: Story = () => (
  <div className="flex flex-col gap-4">
    <div className="flex gap-4 items-center">
      <ActionButton primary isDisabled>
        Primary Disabled
      </ActionButton>
      <ActionButton secondary isDisabled>
        Secondary Disabled
      </ActionButton>
      <ActionButton tertiary isDisabled>
        Tertiary Disabled
      </ActionButton>
    </div>
    <div className="flex gap-4 items-center">
      <ActionButton primary icon={<IconPlus size={18} />} isDisabled>
        Add Item
      </ActionButton>
      <ActionButton secondary icon={<IconSettings size={18} />} isDisabled>
        Settings
      </ActionButton>
      <ActionButton tertiary icon={<IconTrash size={18} />} isDisabled>
        Delete
      </ActionButton>
    </div>
  </div>
);

// ============================================================================
// Full Width
// ============================================================================

export const FullWidth: Story = () => (
  <div className="flex flex-col gap-4 w-64">
    <ActionButton primary fullWidth>
      Full Width Primary
    </ActionButton>
    <ActionButton secondary fullWidth>
      Full Width Secondary
    </ActionButton>
    <ActionButton tertiary fullWidth>
      Full Width Tertiary
    </ActionButton>
  </div>
);

// ============================================================================
// Custom Start Content
// ============================================================================

export const CustomStartContent: Story = () => (
  <div className="flex gap-4 items-center">
    <ActionButton primary startContent={<span className="text-lg">🚀</span>}>
      Launch
    </ActionButton>
    <ActionButton secondary startContent={<span className="text-lg">⚙️</span>}>
      Configure
    </ActionButton>
    <ActionButton tertiary startContent={<span className="text-lg">💡</span>}>
      Ideas
    </ActionButton>
  </div>
);

// ============================================================================
// Danger Actions
// ============================================================================

export const DangerActions: Story = () => (
  <div className="flex gap-4 items-center">
    <ActionButton primary color="danger" icon={<IconTrash size={18} />}>
      Delete
    </ActionButton>
    <ActionButton secondary color="danger" icon={<IconX size={18} />}>
      Remove
    </ActionButton>
    <ActionButton tertiary color="danger" icon={<IconTrash size={18} />}>
      Delete
    </ActionButton>
  </div>
);

// ============================================================================
// Interactive Playground
// ============================================================================

type PlaygroundArgs = {
  variant: 'primary' | 'secondary' | 'tertiary';
  size: 'sm' | 'md' | 'lg';
  color: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'default';
  isLoading: boolean;
  isDisabled: boolean;
  fullWidth: boolean;
  showIcon: boolean;
  label: string;
};

export const Playground: Story<PlaygroundArgs> = ({
  variant = 'primary',
  size = 'md',
  color = 'primary',
  isLoading = false,
  isDisabled = false,
  fullWidth = false,
  showIcon = false,
  label = 'Click Me',
}) => {
  const iconSize = size === 'sm' ? 14 : size === 'lg' ? 22 : 18;
  const icon = showIcon ? <IconSend size={iconSize} /> : undefined;
  const commonProps = {
    size,
    color,
    isLoading,
    isDisabled,
    fullWidth,
    icon,
    onPress: () => alert('Button pressed!'),
  } as const;

  return (
    <div className={fullWidth ? 'w-full' : 'inline-block'}>
      {variant === 'primary' && (
        <ActionButton primary {...commonProps}>
          {label}
        </ActionButton>
      )}
      {variant === 'secondary' && (
        <ActionButton secondary {...commonProps}>
          {label}
        </ActionButton>
      )}
      {variant === 'tertiary' && (
        <ActionButton tertiary {...commonProps}>
          {label}
        </ActionButton>
      )}
    </div>
  );
};

Playground.args = {
  variant: 'primary',
  size: 'md',
  color: 'primary',
  isLoading: false,
  isDisabled: false,
  fullWidth: false,
  showIcon: false,
  label: 'Click Me',
};

Playground.argTypes = {
  variant: {
    control: { type: 'select' },
    options: ['primary', 'secondary', 'tertiary'],
    defaultValue: 'primary',
  },
  size: {
    control: { type: 'select' },
    options: ['sm', 'md', 'lg'],
    defaultValue: 'md',
  },
  color: {
    control: { type: 'select' },
    options: [
      'primary',
      'secondary',
      'success',
      'warning',
      'danger',
      'default',
    ],
    defaultValue: 'primary',
  },
  isLoading: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  isDisabled: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  fullWidth: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  showIcon: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  label: {
    control: { type: 'text' },
    defaultValue: 'Click Me',
  },
};
