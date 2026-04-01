// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
  Tooltip,
} from '@heroui/react';
import { IconDotsVertical } from '@tabler/icons-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ActionButton } from '@amdenterpriseai/components';
import { ActionHintsList } from './ActionHintsList';
import { ActionMenuItem } from './ActionMenuItem';
import { SectionHeader } from './SectionHeader';
import { useMenuKeyboardNavigation } from './useMenuKeyboardNavigation';
import { DropdownItem } from './types';
import { FlattenedDropdownItem, isSectionHeader } from './utils';

interface NestedDropdownProps {
  actions: DropdownItem[];
  isDisabled?: boolean;
  children?: React.ReactNode;
}

// Helper to flatten actions: sections become [header, ...items]
const flattenActionsForDisplay = (
  actions: DropdownItem[],
): FlattenedDropdownItem[] => {
  const result: FlattenedDropdownItem[] = [];
  for (const action of actions) {
    if (action.isSection) {
      // Add section header (non-interactive)
      result.push({ ...action, isSectionHeader: true });
      // Add section items inline
      if (action.actions) {
        result.push(...action.actions);
      }
    } else {
      result.push(action);
    }
  }
  return result;
};

// Recursive component for nested dropdown menus using Popover
const NestedDropdownMenu = ({
  actions,
  onClose,
  onRequestClose,
  isRootLevel = false,
}: {
  actions: DropdownItem[];
  onClose: () => void;
  onRequestClose?: () => void;
  isRootLevel?: boolean;
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Flatten actions to expand sections
  const flattenedActions = flattenActionsForDisplay(actions);

  const { focusedIndex, openKey, setOpenKey, setFocusedIndex, handleKeyDown } =
    useMenuKeyboardNavigation({
      actions: flattenedActions,
      onClose,
      onRequestClose,
      isRootLevel,
    });

  // Auto-focus container when mounted
  useEffect(() => {
    containerRef.current?.focus();
  }, []);

  // Close nested dropdown and return focus to this level
  const handleNestedClose = useCallback(() => {
    setOpenKey(null);
    containerRef.current?.focus();
  }, [setOpenKey]);

  return (
    <div
      ref={containerRef}
      className="flex flex-col gap-0.5 min-w-[200px] outline-none"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      role="menu"
    >
      {flattenedActions.map((action, index) => {
        if (isSectionHeader(action)) {
          return <SectionHeader key={action.key} action={action} />;
        }

        const isFocused = focusedIndex === index;
        const isSubmenuOpen = openKey === action.key;

        return (
          <ActionMenuItem
            key={action.key}
            action={action}
            isFocused={isFocused}
            isSubmenuOpen={isSubmenuOpen}
            onPress={() => {
              action.onPress();
              onClose();
            }}
            onFocus={() => {
              setFocusedIndex(index);
            }}
            onSubmenuOpen={() => setOpenKey(action.key)}
            onSubmenuClose={handleNestedClose}
            onMenuClose={onClose}
            NestedDropdownMenu={NestedDropdownMenu}
          />
        );
      })}
    </div>
  );
};

export const NestedDropdown = ({
  actions,
  isDisabled,
  children,
}: NestedDropdownProps) => {
  const [isOpen, setIsOpen] = useState(false);

  if (actions.length === 0) {
    return null;
  }

  const hints = actions.flatMap((action) => action.hint ?? []);
  const hasHints = hints.length > 0;

  const hintJsx = <ActionHintsList hints={hints} />;

  const handleTriggerKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      setIsOpen(true);
    }
  };

  const MenuContent = (
    <PopoverContent>
      <NestedDropdownMenu
        actions={actions}
        onClose={() => setIsOpen(false)}
        isRootLevel={true}
      />
    </PopoverContent>
  );

  const defaultTrigger = (
    <ActionButton
      tertiary
      size="sm"
      aria-label="Actions menu"
      className="h-auto w-6 min-w-6"
      isDisabled={isDisabled}
      onKeyDown={handleTriggerKeyDown}
      icon={<IconDotsVertical className="text-default-300" />}
    />
  );

  return (
    <Popover isOpen={isOpen} onOpenChange={setIsOpen} placement="bottom-end">
      <PopoverTrigger>{children ?? defaultTrigger}</PopoverTrigger>
      {hasHints ? (
        <Tooltip content={hintJsx}>{MenuContent}</Tooltip>
      ) : (
        MenuContent
      )}
    </Popover>
  );
};

export default NestedDropdown;
