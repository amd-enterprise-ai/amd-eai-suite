// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import { ActionFieldHintType } from '@amdenterpriseai/types';

import { NestedDropdown, DropdownItem } from '@amdenterpriseai/components';

// Mock Tabler icons
vi.mock('@tabler/icons-react', () => ({
  IconDotsVertical: ({ className }: any) => (
    <span className={className}>action-dot-icon</span>
  ),
  IconInfoCircle: ({ className }: any) => (
    <span className={className}>info-icon</span>
  ),
  IconAlertTriangle: ({ className }: any) => (
    <span className={className}>alert-icon</span>
  ),
  IconChevronRight: ({ size }: any) => (
    <span data-testid="chevron-right">chevron-right-{size}</span>
  ),
}));

// Mock HeroUI Tooltip to render content directly
vi.mock('@heroui/react', async () => {
  const actual = await vi.importActual('@heroui/react');
  return {
    ...actual,
    Tooltip: ({ children, content }: any) => (
      <div data-testid="mock-tooltip">
        {children}
        {content && <div data-testid="tooltip-content">{content}</div>}
      </div>
    ),
  };
});

describe('NestedDropdown', () => {
  const createMockActions = (
    overrides: Partial<DropdownItem>[] = [],
  ): DropdownItem[] => [
    {
      key: 'edit',
      label: 'Edit',
      onPress: vi.fn(),
      ...overrides[0],
    },
    {
      key: 'delete',
      label: 'Delete',
      color: 'danger',
      onPress: vi.fn(),
      ...overrides[1],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders correctly with actions', () => {
      const actions = createMockActions();

      render(<NestedDropdown actions={actions} />);

      // Check for the trigger button
      expect(screen.getByText('action-dot-icon')).toBeInTheDocument();
    });

    it('returns null when actions array is empty', () => {
      const { container } = render(<NestedDropdown actions={[]} />);

      expect(container.firstChild).toBeNull();
    });

    it('renders the correct button properties', () => {
      const actions = createMockActions();

      render(<NestedDropdown actions={actions} />);

      const button = screen.getByText('action-dot-icon');
      expect(button.parentElement).toHaveAttribute(
        'aria-label',
        'list.actions.label',
      );
      expect(button.parentElement).toHaveClass('h-auto w-6 min-w-6');
    });

    it('renders the dots vertical icon with correct styling', () => {
      const actions = createMockActions();

      render(<NestedDropdown actions={actions} />);

      const icon = screen.getByText('action-dot-icon');
      expect(icon).toHaveClass('text-default-300');
    });
  });

  describe('Actions rendering', () => {
    it('renders all actions as dropdown items when dropdown is opened', async () => {
      const actions = createMockActions();

      render(<NestedDropdown actions={actions} />);

      // Click the trigger button to open the dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Wait for dropdown items to appear
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument();
        expect(screen.getByText('Delete')).toBeInTheDocument();
      });
    });

    it('applies custom className to dropdown items', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'custom',
          label: 'Custom Action',
          className: 'custom-class',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Wait for dropdown item to appear and check class
      await waitFor(() => {
        const customItem = screen.getByTestId('custom');
        expect(customItem).toHaveClass('custom-class');
      });
    });

    it('applies color-based className to dropdown items', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'danger-action',
          label: 'Danger Action',
          color: 'danger',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Wait for dropdown item to appear and check class
      await waitFor(() => {
        const dangerItem = screen.getByTestId('danger-action');
        expect(dangerItem).toHaveClass('text-danger');
      });
    });

    it('does not apply color class for default color', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'default-action',
          label: 'Default Action',
          color: 'default',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Wait for dropdown item to appear and check class
      await waitFor(() => {
        const defaultItem = screen.getByTestId('default-action');
        expect(defaultItem).not.toHaveClass('text-default');
      });
    });

    it('renders startContent when provided', async () => {
      const startContentTestId = 'start-content';
      const actions: DropdownItem[] = [
        {
          key: 'with-icon',
          label: 'With Icon',
          startContent: <span data-testid={startContentTestId}>Icon</span>,
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Wait for dropdown item to appear
      await waitFor(() => {
        expect(screen.getByTestId(startContentTestId)).toBeInTheDocument();
      });
    });

    it('sets correct aria-label for dropdown items', async () => {
      const actions = createMockActions();

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Wait for dropdown items to appear
      await waitFor(() => {
        expect(screen.getByTestId('edit')).toHaveAttribute(
          'aria-label',
          'Edit',
        );
        expect(screen.getByTestId('delete')).toHaveAttribute(
          'aria-label',
          'Delete',
        );
      });
    });
  });

  describe('Disabled actions', () => {
    it('handles disabled actions correctly', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'enabled',
          label: 'Enabled Action',
          onPress: vi.fn(),
        },
        {
          key: 'disabled',
          label: 'Disabled Action',
          isDisabled: true,
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Check that both actions are rendered
      await waitFor(() => {
        expect(screen.getByText('Enabled Action')).toBeInTheDocument();
        expect(screen.getByText('Disabled Action')).toBeInTheDocument();
      });
    });

    it('handles multiple disabled actions', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'disabled1',
          label: 'Disabled 1',
          isDisabled: true,
          onPress: vi.fn(),
        },
        {
          key: 'disabled2',
          label: 'Disabled 2',
          isDisabled: true,
          onPress: vi.fn(),
        },
        {
          key: 'enabled',
          label: 'Enabled',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Check that all actions are rendered
      await waitFor(() => {
        expect(screen.getByText('Disabled 1')).toBeInTheDocument();
        expect(screen.getByText('Disabled 2')).toBeInTheDocument();
        expect(screen.getByText('Enabled')).toBeInTheDocument();
      });
    });

    it('handles actions with undefined isDisabled property', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'undefined-disabled',
          label: 'Undefined Disabled',
          onPress: vi.fn(),
          // isDisabled is undefined
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Action should be rendered and not disabled
      await waitFor(() => {
        expect(screen.getByText('Undefined Disabled')).toBeInTheDocument();
      });
    });

    it('handles actions with isDisabled as boolean', async () => {
      const mockOnPress1 = vi.fn();
      const mockOnPress2 = vi.fn();

      const actions: DropdownItem[] = [
        {
          key: 'action1',
          label: 'Action 1',
          onPress: mockOnPress1,
          isDisabled: true,
        },
        {
          key: 'action2',
          label: 'Action 2',
          onPress: mockOnPress2,
          isDisabled: false,
        },
      ];

      act(() => {
        render(<NestedDropdown actions={actions} />);
      });

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      const action1 = screen.getByText('Action 1');
      const action2 = screen.getByText('Action 2');

      // Wait for actions to appear
      await waitFor(() => {
        expect(action1).toBeInTheDocument();
        expect(action2).toBeInTheDocument();
      });

      await fireEvent.click(action1);
      await fireEvent.click(action2);

      // Action1 is disabled, so it should not be called. Action2 should be called.
      await waitFor(() => {
        expect(mockOnPress1).not.toBeCalled();
        expect(mockOnPress2).toBeCalled();
      });
    });
  });

  describe('Action handling', () => {
    it('calls the correct action onPress when an action is triggered', async () => {
      const editAction = vi.fn();
      const deleteAction = vi.fn();
      const actions: DropdownItem[] = [
        {
          key: 'edit',
          label: 'Edit',
          onPress: editAction,
        },
        {
          key: 'delete',
          label: 'Delete',
          onPress: deleteAction,
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Click on the edit action
      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument();
      });

      const editItem = screen.getByText('Edit');
      await fireEvent.click(editItem);

      expect(editAction).toHaveBeenCalled();
      expect(deleteAction).not.toHaveBeenCalled();
    });

    it('passes the correct item to the action handler', async () => {
      const actionHandler = vi.fn();
      const customItem = { id: '2', name: 'Custom Item', customProp: 'value' };
      const actions: ActionItem<typeof customItem>[] = [
        {
          key: 'test-action',
          label: 'Test Action',
          onPress: actionHandler,
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Click on the action
      await waitFor(() => {
        expect(screen.getByText('Test Action')).toBeInTheDocument();
      });

      const actionItem = screen.getByText('Test Action');
      await fireEvent.click(actionItem);

      expect(actionHandler).toHaveBeenCalled();
    });

    it('does not trigger action when clicking disabled items', async () => {
      const enabledAction = vi.fn();
      const disabledAction = vi.fn();
      const actions: DropdownItem[] = [
        {
          key: 'enabled-action',
          label: 'Enabled Action',
          onPress: enabledAction,
        },
        {
          key: 'disabled-action',
          label: 'Disabled Action',
          isDisabled: true,
          onPress: disabledAction,
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Wait for items to appear
      await waitFor(() => {
        expect(screen.getByText('Enabled Action')).toBeInTheDocument();
        expect(screen.getByText('Disabled Action')).toBeInTheDocument();
      });

      // Try to click disabled action - it should not trigger
      const disabledItem = screen.getByText('Disabled Action');
      await fireEvent.click(disabledItem);

      expect(disabledAction).not.toHaveBeenCalled();
      expect(enabledAction).not.toHaveBeenCalled();
    });
  });

  describe('Edge cases', () => {
    it('handles actions with undefined isDisabled property', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'undefined-disabled',
          label: 'Undefined Disabled',
          onPress: vi.fn(),
          // isDisabled is undefined
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Action should be rendered and not disabled
      await waitFor(() => {
        expect(screen.getByText('Undefined Disabled')).toBeInTheDocument();
      });
    });

    it('handles empty action label', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'empty-label',
          label: '',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Action should be rendered even with empty label
      await waitFor(() => {
        const actionItem = screen.getByTestId('empty-label');
        expect(actionItem).toBeInTheDocument();
        expect(actionItem).toHaveTextContent('');
      });
    });

    it('handles complex className combinations', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'complex-class',
          label: 'Complex Class',
          className: 'custom-class another-class',
          color: 'warning',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Check combined classes
      await waitFor(() => {
        const actionItem = screen.getByTestId('complex-class');
        expect(actionItem).toHaveClass(
          'custom-class another-class text-warning',
        );
      });
    });
  });

  describe('Container structure', () => {
    it('renders the correct container structure', () => {
      const actions = createMockActions();
      const { container } = render(<NestedDropdown actions={actions} />);

      const outerDiv = container.firstChild as HTMLElement;
      expect(outerDiv).toHaveClass(
        'relative flex justify-center items-center gap-2',
      );
    });
  });

  describe('Hint rendering', () => {
    it('renders hints when provided', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'action-with-hint',
          label: 'Action with Hint',
          onPress: vi.fn(),
          hint: [
            {
              message: 'This is an info hint',
              type: ActionFieldHintType.INFO,
            },
            {
              message: 'This is a warning hint',
              type: ActionFieldHintType.WARNING,
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Wait for hints to appear (they're rendered immediately with the mock)
      await waitFor(() => {
        expect(screen.getByText('This is an info hint')).toBeInTheDocument();
        expect(screen.getByText('This is a warning hint')).toBeInTheDocument();
        expect(
          screen.getByText('This is an info hint').previousSibling,
        ).toHaveClass('text-info');
        expect(
          screen.getByText('This is a warning hint').previousSibling,
        ).toHaveClass('text-warning');
      });
    });

    it('does not render hints when not provided', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'action-with-hint',
          label: 'Action with Hint',
          onPress: vi.fn(),
          hint: [], // No hints (pre-filtered)
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Ensure no hints appear
      await waitFor(() => {
        expect(screen.getByText('Action with Hint')).toBeInTheDocument();
      });
    });

    it('handles multiple hints with pre-filtering', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'action-with-mixed-hints',
          label: 'Action with Mixed Hints',
          onPress: vi.fn(),
          hint: [
            {
              message: 'Visible Hint',
              type: ActionFieldHintType.INFO,
            },
            // Hidden hint is not included (pre-filtered at action creation)
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      // Open dropdown
      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      // Check that only the visible hint appears
      await waitFor(() => {
        expect(screen.getByText('Visible Hint')).toBeInTheDocument();
      });
    });
  });

  describe('Description rendering', () => {
    it('renders string description when provided', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'action-with-description',
          label: 'Action with Description',
          description: 'This is a description',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Action with Description')).toBeInTheDocument();
        expect(screen.getByText('This is a description')).toBeInTheDocument();
      });
    });

    it('renders ReactNode description when provided', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'action-with-node-description',
          label: 'Action with Node Description',
          description: (
            <span data-testid="custom-description">Custom description</span>
          ),
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(
          screen.getByText('Action with Node Description'),
        ).toBeInTheDocument();
        expect(screen.getByTestId('custom-description')).toBeInTheDocument();
      });
    });

    it('renders description alongside other props', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'complex-action',
          label: 'Complex Action',
          description: 'Description text',
          startContent: <span data-testid="start-icon">Icon</span>,
          color: 'primary',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Complex Action')).toBeInTheDocument();
        expect(screen.getByText('Description text')).toBeInTheDocument();
        expect(screen.getByTestId('start-icon')).toBeInTheDocument();
      });
    });

    it('works without description (undefined)', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'action-no-description',
          label: 'No Description',
          onPress: vi.fn(),
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('No Description')).toBeInTheDocument();
      });
    });
  });

  describe('Nested dropdown rendering', () => {
    it('renders nested dropdown when actions array exists', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'parent',
          label: 'Parent Action',
          onPress: vi.fn(),
          actions: [
            {
              key: 'child1',
              label: 'Child 1',
              onPress: vi.fn(),
            },
            {
              key: 'child2',
              label: 'Child 2',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Parent Action')).toBeInTheDocument();
      });
    });

    it('displays chevron icon for nested items', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'parent',
          label: 'Parent Action',
          onPress: vi.fn(),
          actions: [
            {
              key: 'child',
              label: 'Child',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByTestId('chevron-right')).toBeInTheDocument();
        expect(screen.getByText('chevron-right-16')).toBeInTheDocument();
      });
    });

    it('handles multiple levels of nesting', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'level1',
          label: 'Level 1',
          onPress: vi.fn(),
          actions: [
            {
              key: 'level2',
              label: 'Level 2',
              onPress: vi.fn(),
              actions: [
                {
                  key: 'level3',
                  label: 'Level 3',
                  onPress: vi.fn(),
                },
              ],
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Level 1')).toBeInTheDocument();
      });
    });

    it('nested items have proper description support', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'parent',
          label: 'Parent',
          description: 'Parent description',
          onPress: vi.fn(),
          actions: [
            {
              key: 'child',
              label: 'Child',
              description: 'Child description',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Parent')).toBeInTheDocument();
        expect(screen.getByText('Parent description')).toBeInTheDocument();
      });
    });

    it('mixes nested and regular items', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'regular',
          label: 'Regular Action',
          onPress: vi.fn(),
        },
        {
          key: 'nested',
          label: 'Nested Action',
          onPress: vi.fn(),
          actions: [
            {
              key: 'child',
              label: 'Child Action',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Regular Action')).toBeInTheDocument();
        expect(screen.getByText('Nested Action')).toBeInTheDocument();
        expect(screen.getByTestId('chevron-right')).toBeInTheDocument();
      });
    });
  });

  describe('Nested dropdown interaction', () => {
    it('regular items call onPress handler', async () => {
      const onPressMock = vi.fn();
      const actions: DropdownItem[] = [
        {
          key: 'regular',
          label: 'Regular Action',
          onPress: onPressMock,
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Regular Action')).toBeInTheDocument();
      });

      const regularItem = screen.getByText('Regular Action');
      await fireEvent.click(regularItem);

      expect(onPressMock).toHaveBeenCalled();
    });

    it('nested items do NOT call parent onPress', async () => {
      const parentOnPress = vi.fn();
      const childOnPress = vi.fn();
      const actions: DropdownItem[] = [
        {
          key: 'parent',
          label: 'Parent Action',
          onPress: parentOnPress,
          actions: [
            {
              key: 'child',
              label: 'Child Action',
              onPress: childOnPress,
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Parent Action')).toBeInTheDocument();
      });

      expect(parentOnPress).not.toHaveBeenCalled();
    });

    it('disabled state works for nested items', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'parent',
          label: 'Parent',
          onPress: vi.fn(),
          isDisabled: true,
          actions: [
            {
              key: 'child',
              label: 'Child',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Parent')).toBeInTheDocument();
      });
    });
  });

  describe('Edge cases with nested dropdowns', () => {
    it('empty nested actions array renders as regular item', async () => {
      const onPressMock = vi.fn();
      const actions: DropdownItem[] = [
        {
          key: 'action',
          label: 'Action',
          onPress: onPressMock,
          actions: [],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Action')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('chevron-right')).not.toBeInTheDocument();

      const actionItem = screen.getByText('Action');
      await fireEvent.click(actionItem);

      expect(onPressMock).toHaveBeenCalled();
    });

    it('nested item with description and nested actions', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'parent',
          label: 'Parent',
          description: 'Parent desc',
          onPress: vi.fn(),
          actions: [
            {
              key: 'child',
              label: 'Child',
              description: 'Child desc',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Parent')).toBeInTheDocument();
        expect(screen.getByText('Parent desc')).toBeInTheDocument();
        expect(screen.getByTestId('chevron-right')).toBeInTheDocument();
      });
    });

    it('hints only collected from top-level actions', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'parent',
          label: 'Parent',
          onPress: vi.fn(),
          hint: [
            {
              message: 'Top-level hint',
              type: ActionFieldHintType.INFO,
            },
          ],
          actions: [
            {
              key: 'child',
              label: 'Child',
              onPress: vi.fn(),
              hint: [
                {
                  message: 'Nested hint',
                  type: ActionFieldHintType.WARNING,
                },
              ],
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      await waitFor(() => {
        expect(screen.getByText('Top-level hint')).toBeInTheDocument();
        expect(screen.queryByText('Nested hint')).not.toBeInTheDocument();
      });
    });
  });

  describe('Section rendering', () => {
    it('renders section with title only', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'section',
          label: 'Section Title',
          onPress: vi.fn(),
          isSection: true,
          actions: [
            {
              key: 'item1',
              label: 'Item 1',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByTestId('section-section')).toBeInTheDocument();
        expect(screen.getByText('Section Title')).toBeInTheDocument();
        expect(screen.getByText('Item 1')).toBeInTheDocument();
      });
    });

    it('renders section with title and description', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'section',
          label: 'Section Title',
          description: 'Section Description',
          onPress: vi.fn(),
          isSection: true,
          actions: [
            {
              key: 'item1',
              label: 'Item 1',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Section Title')).toBeInTheDocument();
        expect(screen.getByText('Section Description')).toBeInTheDocument();
        expect(screen.getByText('Item 1')).toBeInTheDocument();
      });
    });

    it('renders section items at same visual level', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'regular',
          label: 'Regular Action',
          onPress: vi.fn(),
        },
        {
          key: 'section',
          label: 'Section',
          onPress: vi.fn(),
          isSection: true,
          actions: [
            {
              key: 'item1',
              label: 'Section Item 1',
              onPress: vi.fn(),
            },
            {
              key: 'item2',
              label: 'Section Item 2',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Regular Action')).toBeInTheDocument();
        expect(screen.getByText('Section')).toBeInTheDocument();
        expect(screen.getByText('Section Item 1')).toBeInTheDocument();
        expect(screen.getByText('Section Item 2')).toBeInTheDocument();
      });

      // Verify all items are rendered at the same level (no nested popover for section)
      const sectionHeader = screen.getByTestId('section-section');
      expect(sectionHeader).toHaveAttribute('role', 'presentation');
    });

    it('section items are clickable and call onPress', async () => {
      const onPressMock = vi.fn();
      const actions: DropdownItem[] = [
        {
          key: 'section',
          label: 'Section',
          onPress: vi.fn(),
          isSection: true,
          actions: [
            {
              key: 'item1',
              label: 'Clickable Item',
              onPress: onPressMock,
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Clickable Item')).toBeInTheDocument();
      });

      const item = screen.getByText('Clickable Item');
      await fireEvent.click(item);

      expect(onPressMock).toHaveBeenCalled();
    });

    it('empty section renders just header', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'empty-section',
          label: 'Empty Section',
          onPress: vi.fn(),
          isSection: true,
          actions: [],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Empty Section')).toBeInTheDocument();
        expect(screen.getByTestId('section-empty-section')).toBeInTheDocument();
      });
    });

    it('mixed sections and regular actions', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'action1',
          label: 'Action 1',
          onPress: vi.fn(),
        },
        {
          key: 'section1',
          label: 'Section 1',
          onPress: vi.fn(),
          isSection: true,
          actions: [
            {
              key: 'section1-item1',
              label: 'Section 1 Item',
              onPress: vi.fn(),
            },
          ],
        },
        {
          key: 'action2',
          label: 'Action 2',
          onPress: vi.fn(),
        },
        {
          key: 'section2',
          label: 'Section 2',
          onPress: vi.fn(),
          isSection: true,
          actions: [
            {
              key: 'section2-item1',
              label: 'Section 2 Item',
              onPress: vi.fn(),
            },
          ],
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Action 1')).toBeInTheDocument();
        expect(screen.getByText('Section 1')).toBeInTheDocument();
        expect(screen.getByText('Section 1 Item')).toBeInTheDocument();
        expect(screen.getByText('Action 2')).toBeInTheDocument();
        expect(screen.getByText('Section 2')).toBeInTheDocument();
        expect(screen.getByText('Section 2 Item')).toBeInTheDocument();
      });
    });

    it('section without actions property renders just header', async () => {
      const actions: DropdownItem[] = [
        {
          key: 'section-no-actions',
          label: 'Section No Actions',
          onPress: vi.fn(),
          isSection: true,
        },
      ];

      render(<NestedDropdown actions={actions} />);

      const triggerButton = screen.getByText('action-dot-icon');
      await fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Section No Actions')).toBeInTheDocument();
        expect(
          screen.getByTestId('section-section-no-actions'),
        ).toBeInTheDocument();
      });
    });
  });
});
