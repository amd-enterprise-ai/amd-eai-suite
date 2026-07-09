// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSection,
  DropdownTrigger,
} from '../../../src/Dropdown/DropdownPrimitive';

export default {
  title: 'Components/Dropdown',
} satisfies StoryDefault;

// ============================================================================
// Basic dropdown
// ============================================================================

export const Basic: Story = () => (
  <Dropdown>
    <DropdownTrigger>
      <button className="px-4 py-2 bg-primary text-white rounded-md text-sm">
        Open Dropdown
      </button>
    </DropdownTrigger>
    <DropdownMenu aria-label="Actions">
      <DropdownItem key="new">New file</DropdownItem>
      <DropdownItem key="copy">Copy link</DropdownItem>
      <DropdownItem key="edit">Edit file</DropdownItem>
      <DropdownItem key="delete" className="text-danger" color="danger">
        Delete file
      </DropdownItem>
    </DropdownMenu>
  </Dropdown>
);

// ============================================================================
// Compound form
// ============================================================================

export const CompoundForm: Story = () => (
  <Dropdown>
    <Dropdown.Trigger>
      <button className="px-4 py-2 bg-primary text-white rounded-md text-sm">
        Compound Dropdown
      </button>
    </Dropdown.Trigger>
    <Dropdown.Menu aria-label="Actions">
      <Dropdown.Item key="new">New file</Dropdown.Item>
      <Dropdown.Item key="copy">Copy link</Dropdown.Item>
      <Dropdown.Item key="delete" className="text-danger" color="danger">
        Delete
      </Dropdown.Item>
    </Dropdown.Menu>
  </Dropdown>
);

// ============================================================================
// With sections
// ============================================================================

export const WithSections: Story = () => (
  <Dropdown>
    <DropdownTrigger>
      <button className="px-4 py-2 bg-primary text-white rounded-md text-sm">
        With Sections
      </button>
    </DropdownTrigger>
    <DropdownMenu aria-label="Actions with sections">
      <DropdownSection title="Actions">
        <DropdownItem key="new">New file</DropdownItem>
        <DropdownItem key="copy">Copy link</DropdownItem>
      </DropdownSection>
      <DropdownSection title="Danger Zone">
        <DropdownItem key="delete" className="text-danger" color="danger">
          Delete file
        </DropdownItem>
      </DropdownSection>
    </DropdownMenu>
  </Dropdown>
);

// ============================================================================
// Disabled keys
// ============================================================================

export const DisabledKeys: Story = () => (
  <Dropdown>
    <DropdownTrigger>
      <button className="px-4 py-2 bg-primary text-white rounded-md text-sm">
        With Disabled Keys
      </button>
    </DropdownTrigger>
    <DropdownMenu aria-label="Actions" disabledKeys={['edit', 'delete']}>
      <DropdownItem key="new">New file</DropdownItem>
      <DropdownItem key="copy">Copy link</DropdownItem>
      <DropdownItem key="edit">Edit file (disabled)</DropdownItem>
      <DropdownItem key="delete">Delete file (disabled)</DropdownItem>
    </DropdownMenu>
  </Dropdown>
);
