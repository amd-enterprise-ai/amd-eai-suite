// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Button, ButtonGroup } from '../../../src/Buttons';
import type { ButtonProps } from '../../../src/Buttons';
import {
  IconPlus,
  IconArrowRight,
  IconDownload,
  IconLoaderQuarter,
  IconSettings,
  IconTrash,
} from '@tabler/icons-react';

export default {
  title: 'Components/Buttons/Button',
} satisfies StoryDefault;

// ============================================================================
// Variants
// ============================================================================

const VARIANTS: ButtonProps['variant'][] = [
  'solid',
  'bordered',
  'light',
  'flat',
  'faded',
  'shadow',
  'ghost',
];

export const Variants: Story = () => (
  <div className="flex flex-wrap gap-4">
    {VARIANTS.map((variant) => (
      <Button key={variant} color="primary" variant={variant}>
        {variant}
      </Button>
    ))}
  </div>
);

// ============================================================================
// Colors
// ============================================================================

const COLORS: ButtonProps['color'][] = [
  'default',
  'primary',
  'secondary',
  'success',
  'warning',
  'danger',
];

export const Colors: Story = () => (
  <div className="flex flex-wrap gap-4">
    {COLORS.map((color) => (
      <Button key={color} color={color}>
        {color}
      </Button>
    ))}
  </div>
);

// ============================================================================
// Sizes
// ============================================================================

export const Sizes: Story = () => (
  <div className="flex items-center gap-4">
    <Button color="primary" size="sm">
      Small
    </Button>
    <Button color="primary" size="md">
      Medium
    </Button>
    <Button color="primary" size="lg">
      Large
    </Button>
  </div>
);

// ============================================================================
// Radius
// ============================================================================

const RADII: ButtonProps['radius'][] = ['none', 'sm', 'md', 'lg', 'full'];

export const Radius: Story = () => (
  <div className="flex flex-wrap items-center gap-4">
    {RADII.map((radius) => (
      <Button key={radius} color="primary" radius={radius}>
        {radius}
      </Button>
    ))}
  </div>
);

// ============================================================================
// With Icons
// ============================================================================

export const WithIcons: Story = () => (
  <div className="flex flex-wrap items-center gap-4">
    <Button color="primary" startContent={<IconPlus size={18} />}>
      Add Item
    </Button>
    <Button color="default" endContent={<IconArrowRight size={18} />}>
      Continue
    </Button>
    <Button
      color="default"
      variant="flat"
      startContent={<IconDownload size={18} />}
    >
      Download
    </Button>
  </div>
);

export const IconOnly: Story = () => (
  <div className="flex items-center gap-4">
    <Button color="primary" isIconOnly aria-label="Add">
      <IconPlus size={18} />
    </Button>
    <Button color="default" variant="flat" isIconOnly aria-label="Settings">
      <IconSettings size={18} />
    </Button>
    <Button color="danger" variant="light" isIconOnly aria-label="Delete">
      <IconTrash size={18} />
    </Button>
  </div>
);

// ============================================================================
// States
// ============================================================================

export const Loading: Story = () => (
  <div className="flex flex-wrap items-center gap-4">
    <Button color="primary" isLoading>
      Saving...
    </Button>
    <Button
      color="default"
      variant="flat"
      isLoading
      spinner={<IconLoaderQuarter className="animate-spin" />}
    >
      Custom Spinner
    </Button>
  </div>
);

export const Disabled: Story = () => (
  <div className="flex flex-wrap items-center gap-4">
    <Button color="primary" isDisabled>
      Primary
    </Button>
    <Button color="default" variant="flat" isDisabled>
      Flat
    </Button>
    <Button color="danger" variant="light" isDisabled>
      Light Danger
    </Button>
  </div>
);

// ============================================================================
// Full Width
// ============================================================================

export const FullWidth: Story = () => (
  <div className="flex w-64 flex-col gap-4">
    <Button color="primary" fullWidth>
      Full Width Primary
    </Button>
    <Button color="default" variant="flat" fullWidth>
      Full Width Flat
    </Button>
  </div>
);

// ============================================================================
// Button Group
// ============================================================================

export const Group: Story = () => (
  <ButtonGroup>
    <Button color="primary">Left</Button>
    <Button color="primary" variant="flat">
      Center
    </Button>
    <Button color="primary">Right</Button>
  </ButtonGroup>
);

export const GroupVariants: Story = () => (
  <div className="flex flex-col gap-4">
    <ButtonGroup color="primary" variant="solid">
      <Button>One</Button>
      <Button>Two</Button>
      <Button>Three</Button>
    </ButtonGroup>
    <ButtonGroup color="secondary" variant="bordered">
      <Button>One</Button>
      <Button>Two</Button>
      <Button>Three</Button>
    </ButtonGroup>
    <ButtonGroup color="default" variant="flat" size="sm">
      <Button>One</Button>
      <Button>Two</Button>
      <Button>Three</Button>
    </ButtonGroup>
  </div>
);

// ============================================================================
// Interactive Playground
// ============================================================================

type PlaygroundArgs = {
  variant: NonNullable<ButtonProps['variant']>;
  color: NonNullable<ButtonProps['color']>;
  size: NonNullable<ButtonProps['size']>;
  radius: NonNullable<ButtonProps['radius']>;
  isDisabled: boolean;
  isLoading: boolean;
  fullWidth: boolean;
  showStartIcon: boolean;
  label: string;
};

export const Playground: Story<PlaygroundArgs> = ({
  variant = 'solid',
  color = 'primary',
  size = 'md',
  radius = 'md',
  isDisabled = false,
  isLoading = false,
  fullWidth = false,
  showStartIcon = false,
  label = 'Click Me',
}) => {
  const iconSize = size === 'sm' ? 14 : size === 'lg' ? 22 : 18;

  return (
    <div className={fullWidth ? 'w-full' : 'inline-block'}>
      <Button
        variant={variant}
        color={color}
        size={size}
        radius={radius}
        isDisabled={isDisabled}
        isLoading={isLoading}
        fullWidth={fullWidth}
        startContent={showStartIcon ? <IconPlus size={iconSize} /> : undefined}
        onPress={() => alert('Button pressed!')}
      >
        {label}
      </Button>
    </div>
  );
};

Playground.args = {
  variant: 'solid',
  color: 'primary',
  size: 'md',
  radius: 'md',
  isDisabled: false,
  isLoading: false,
  fullWidth: false,
  showStartIcon: false,
  label: 'Click Me',
};

Playground.argTypes = {
  variant: {
    control: { type: 'select' },
    options: ['solid', 'bordered', 'light', 'flat', 'faded', 'shadow', 'ghost'],
    defaultValue: 'solid',
  },
  color: {
    control: { type: 'select' },
    options: [
      'default',
      'primary',
      'secondary',
      'success',
      'warning',
      'danger',
    ],
    defaultValue: 'primary',
  },
  size: {
    control: { type: 'select' },
    options: ['sm', 'md', 'lg'],
    defaultValue: 'md',
  },
  radius: {
    control: { type: 'select' },
    options: ['none', 'sm', 'md', 'lg', 'full'],
    defaultValue: 'md',
  },
  isDisabled: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  isLoading: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  fullWidth: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  showStartIcon: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  label: {
    control: { type: 'text' },
    defaultValue: 'Click Me',
  },
};
