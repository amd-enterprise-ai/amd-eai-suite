// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Card, CardBody, CardHeader, CardFooter } from '../../../src/Card';

export default {
  title: 'Components/Card',
} satisfies StoryDefault;

// ============================================================================
// Compound API — the adapter exposes both flat parts and Card.* subcomponents
// ============================================================================

export const FlatImports: Story = () => (
  <div className="w-full max-w-sm p-4">
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold">Flat import usage</h3>
      </CardHeader>
      <CardBody>
        <p>Body rendered with the flat CardBody import.</p>
      </CardBody>
      <CardFooter>
        <p className="text-sm text-default-500">Footer</p>
      </CardFooter>
    </Card>
  </div>
);

export const CompoundSyntax: Story = () => (
  <div className="w-full max-w-sm p-4">
    <Card>
      <Card.Header>
        <h3 className="text-lg font-semibold">Compound syntax usage</h3>
      </Card.Header>
      <Card.Body>
        <p>Body rendered with the Card.Body compound subcomponent.</p>
      </Card.Body>
      <Card.Footer>
        <p className="text-sm text-default-500">Footer</p>
      </Card.Footer>
    </Card>
  </div>
);

// ============================================================================
// Variants
// ============================================================================

export const Shadows: Story = () => (
  <div className="flex flex-wrap gap-6 p-4">
    {(['none', 'sm', 'md', 'lg'] as const).map((shadow) => (
      <Card key={shadow} shadow={shadow} className="w-48">
        <Card.Header>
          <h3 className="text-base font-semibold">shadow="{shadow}"</h3>
        </Card.Header>
        <Card.Body>
          <p className="text-sm text-default-500">Elevation variant.</p>
        </Card.Body>
      </Card>
    ))}
  </div>
);

export const Radius: Story = () => (
  <div className="flex flex-wrap gap-6 p-4">
    {(['none', 'sm', 'md', 'lg'] as const).map((radius) => (
      <Card key={radius} radius={radius} shadow="sm" className="w-48">
        <Card.Header>
          <h3 className="text-base font-semibold">radius="{radius}"</h3>
        </Card.Header>
        <Card.Body>
          <p className="text-sm text-default-500">Corner radius variant.</p>
        </Card.Body>
      </Card>
    ))}
  </div>
);

export const Hoverable: Story = () => (
  <div className="w-full max-w-sm p-4">
    <Card isHoverable shadow="sm">
      <Card.Header>
        <h3 className="text-base font-semibold">Hoverable</h3>
      </Card.Header>
      <Card.Body>
        <p className="text-sm text-default-500">
          Hover over the card to see the elevation change.
        </p>
      </Card.Body>
    </Card>
  </div>
);

export const Pressable: Story = () => (
  <div className="w-full max-w-sm p-4">
    <Card isPressable shadow="sm" onPress={() => alert('Card pressed!')}>
      <Card.Header>
        <h3 className="text-base font-semibold">Pressable</h3>
      </Card.Header>
      <Card.Body>
        <p className="text-sm text-default-500">Click to trigger onPress.</p>
      </Card.Body>
    </Card>
  </div>
);

export const FullWidth: Story = () => (
  <div className="w-full p-4">
    <Card fullWidth shadow="sm">
      <Card.Header>
        <h3 className="text-base font-semibold">Full width</h3>
      </Card.Header>
      <Card.Body>
        <p className="text-sm text-default-500">
          The card stretches to fill its container.
        </p>
      </Card.Body>
    </Card>
  </div>
);

export const Disabled: Story = () => (
  <div className="w-full max-w-sm p-4">
    <Card isPressable isDisabled shadow="sm" onPress={() => alert('nope')}>
      <Card.Header>
        <h3 className="text-base font-semibold">Disabled</h3>
      </Card.Header>
      <Card.Body>
        <p className="text-sm text-default-500">
          A disabled pressable card does not respond to interaction.
        </p>
      </Card.Body>
    </Card>
  </div>
);

export const HeaderBodyFooter: Story = () => (
  <div className="w-full max-w-sm p-4">
    <Card shadow="md">
      <Card.Header className="flex flex-col items-start gap-1">
        <h3 className="text-lg font-semibold">Workload summary</h3>
        <span className="text-xs text-default-500">Updated just now</span>
      </Card.Header>
      <Card.Body className="gap-2">
        <div className="flex justify-between text-sm">
          <span className="text-default-500">Status</span>
          <span className="font-medium">Running</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-default-500">Replicas</span>
          <span className="font-medium">3 / 3</span>
        </div>
      </Card.Body>
      <Card.Footer className="justify-end">
        <span className="text-xs text-default-500">View details</span>
      </Card.Footer>
    </Card>
  </div>
);

// ============================================================================
// Interactive Playground
// ============================================================================

type PlaygroundArgs = {
  shadow: 'none' | 'sm' | 'md' | 'lg';
  radius: 'none' | 'sm' | 'md' | 'lg';
  fullWidth: boolean;
  isHoverable: boolean;
  isPressable: boolean;
  isDisabled: boolean;
  showHeader: boolean;
  showFooter: boolean;
};

export const Playground: Story<PlaygroundArgs> = ({
  shadow = 'md',
  radius = 'lg',
  fullWidth = false,
  isHoverable = false,
  isPressable = false,
  isDisabled = false,
  showHeader = true,
  showFooter = true,
}) => (
  <div className={fullWidth ? 'w-full p-4' : 'w-full max-w-sm p-4'}>
    <Card
      shadow={shadow}
      radius={radius}
      fullWidth={fullWidth}
      isHoverable={isHoverable}
      isPressable={isPressable}
      isDisabled={isDisabled}
      onPress={isPressable ? () => alert('Card pressed!') : undefined}
    >
      {showHeader && (
        <Card.Header>
          <h3 className="text-base font-semibold">Playground</h3>
        </Card.Header>
      )}
      <Card.Body>
        <p className="text-sm text-default-500">
          Toggle the controls to explore the adapter&apos;s public API.
        </p>
      </Card.Body>
      {showFooter && (
        <Card.Footer>
          <span className="text-xs text-default-500">Footer</span>
        </Card.Footer>
      )}
    </Card>
  </div>
);

Playground.args = {
  shadow: 'md',
  radius: 'lg',
  fullWidth: false,
  isHoverable: false,
  isPressable: false,
  isDisabled: false,
  showHeader: true,
  showFooter: true,
};

Playground.argTypes = {
  shadow: {
    control: { type: 'select' },
    options: ['none', 'sm', 'md', 'lg'],
    defaultValue: 'md',
  },
  radius: {
    control: { type: 'select' },
    options: ['none', 'sm', 'md', 'lg'],
    defaultValue: 'lg',
  },
  fullWidth: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  isHoverable: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  isPressable: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  isDisabled: {
    control: { type: 'boolean' },
    defaultValue: false,
  },
  showHeader: {
    control: { type: 'boolean' },
    defaultValue: true,
  },
  showFooter: {
    control: { type: 'boolean' },
    defaultValue: true,
  },
};
