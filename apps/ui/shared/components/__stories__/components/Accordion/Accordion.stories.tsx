// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { Accordion, AccordionItem } from '../../../src/Accordion/Accordion';

export default {
  title: 'Components/Accordion',
} satisfies StoryDefault;

// ============================================================================
// Compound form
// ============================================================================

export const CompoundForm: Story = () => (
  <Accordion>
    <Accordion.Item key="a" aria-label="Section A" title="Section A">
      Content for section A. This uses the compound Accordion.Item pattern.
    </Accordion.Item>
    <Accordion.Item key="b" aria-label="Section B" title="Section B">
      Content for section B. Click the header to toggle.
    </Accordion.Item>
    <Accordion.Item key="c" aria-label="Section C" title="Section C">
      Content for section C.
    </Accordion.Item>
  </Accordion>
);

// ============================================================================
// Flat alias form
// ============================================================================

export const FlatAliasForm: Story = () => (
  <Accordion>
    <AccordionItem key="a" aria-label="Section A" title="Section A">
      Content for section A using the flat AccordionItem alias.
    </AccordionItem>
    <AccordionItem key="b" aria-label="Section B" title="Section B">
      Content for section B.
    </AccordionItem>
  </Accordion>
);

// ============================================================================
// Default expanded
// ============================================================================

export const DefaultExpanded: Story = () => (
  <Accordion defaultSelectedKeys={['a']}>
    <Accordion.Item
      key="a"
      aria-label="Open by default"
      title="Open by default"
    >
      This item is expanded by default via defaultSelectedKeys.
    </Accordion.Item>
    <Accordion.Item
      key="b"
      aria-label="Collapsed by default"
      title="Collapsed by default"
    >
      This item starts collapsed.
    </Accordion.Item>
  </Accordion>
);

// ============================================================================
// Selectionmode
// ============================================================================

export const MultipleSelection: Story = () => (
  <Accordion selectionMode="multiple">
    <Accordion.Item key="a" aria-label="Item A" title="Item A">
      Multiple items can be open at once.
    </Accordion.Item>
    <Accordion.Item key="b" aria-label="Item B" title="Item B">
      Open me at the same time as Item A.
    </Accordion.Item>
    <Accordion.Item key="c" aria-label="Item C" title="Item C">
      Or open all three simultaneously.
    </Accordion.Item>
  </Accordion>
);
