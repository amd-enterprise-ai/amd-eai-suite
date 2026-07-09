// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';

import { BreadcrumbItem, Breadcrumbs } from '../../../src/Breadcrumbs';

export default {
  title: 'Components/Breadcrumbs',
} satisfies StoryDefault;

export const FlatImports: Story = () => (
  <div className="p-4">
    <Breadcrumbs aria-label="Flat breadcrumb trail" size="lg">
      <BreadcrumbItem href="/projects">Projects</BreadcrumbItem>
      <BreadcrumbItem href="/projects/alpha">Alpha</BreadcrumbItem>
      <BreadcrumbItem>Overview</BreadcrumbItem>
    </Breadcrumbs>
  </div>
);

export const CompoundSyntax: Story = () => (
  <div className="p-4">
    <Breadcrumbs aria-label="Compound breadcrumb trail" size="lg">
      <Breadcrumbs.Item href="/home">Home</Breadcrumbs.Item>
      <Breadcrumbs.Item href="/models">Models</Breadcrumbs.Item>
      <Breadcrumbs.Item>Custom model</Breadcrumbs.Item>
    </Breadcrumbs>
  </div>
);
