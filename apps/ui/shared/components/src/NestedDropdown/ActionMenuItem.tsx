// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Popover, PopoverContent, PopoverTrigger, cn } from '@heroui/react';
import { IconChevronRight } from '@tabler/icons-react';

import { DropdownItem } from './types';
import { isActionDisabled } from './utils';

const buildMenuItemClasses = (action: DropdownItem) => {
  return cn(
    'group',
    'relative',
    'flex',
    'w-full',
    'items-center',
    'justify-between',
    'gap-2',
    'p-1.5',
    'text-left',
    'rounded-small',
    'outline-none',
    'cursor-pointer',
    'transition-colors',
    'data-[hover=true]:bg-default-100',
    'data-[focus=true]:bg-default-100',
    'data-[disabled=true]:cursor-not-allowed',
    'data-[disabled=true]:opacity-50',
    action.color &&
      action.color !== 'text-foreground' &&
      `text-${action.color}`,
    action.className,
  );
};

interface ActionMenuItemProps {
  action: DropdownItem;
  isFocused: boolean;
  isSubmenuOpen?: boolean;
  onPress: () => void;
  onFocus: () => void;
  onSubmenuOpen?: () => void;
  onSubmenuClose?: () => void;
  onMenuClose: () => void;
  NestedDropdownMenu: React.ComponentType<{
    actions: DropdownItem[];
    onClose: () => void;
    onRequestClose?: () => void;
  }>;
}

export const ActionMenuItem = ({
  action,
  isFocused,
  isSubmenuOpen,
  onPress,
  onFocus,
  onSubmenuOpen,
  onSubmenuClose,
  onMenuClose,
  NestedDropdownMenu,
}: ActionMenuItemProps) => {
  const disabled = isActionDisabled(action);
  const hasSubmenu = action.actions && action.actions.length > 0;

  const content = (
    <>
      <div className="flex flex-row gap-0 items-center w-full">
        <div className="flex flex-row items-center justify-start gap-2">
          {action.startContent}
        </div>
        <div className="flex flex-col items-center justify-start gap-0 grow">
          <div className="w-full text-small font-normal">{action.label}</div>
          {action.description && (
            <div className="w-full text-tiny text-foreground-500">
              {action.description}
            </div>
          )}
        </div>
        {hasSubmenu && (
          <IconChevronRight size={16} className="text-foreground-500" />
        )}
      </div>
    </>
  );

  const buttonProps = {
    className: buildMenuItemClasses(action),
    disabled,
    'data-testid': action.key,
    'aria-label': action.label,
    'data-focus': isFocused || undefined,
    'data-disabled': disabled || undefined,
    role: 'menuitem' as const,
  };

  if (hasSubmenu) {
    return (
      <Popover
        placement="right-start"
        offset={10}
        isOpen={isSubmenuOpen}
        onOpenChange={(open) => (open ? onSubmenuOpen?.() : onSubmenuClose?.())}
      >
        <PopoverTrigger>
          <button
            {...buttonProps}
            data-hover={isSubmenuOpen || undefined}
            aria-haspopup="menu"
            aria-expanded={isSubmenuOpen}
            onMouseEnter={() => {
              onSubmenuOpen?.();
              onFocus();
            }}
            onClick={(e) => {
              e.preventDefault();
              onSubmenuOpen?.();
            }}
          >
            {content}
          </button>
        </PopoverTrigger>
        <PopoverContent onMouseLeave={onSubmenuClose}>
          <NestedDropdownMenu
            actions={action.actions!}
            onClose={onMenuClose}
            onRequestClose={onSubmenuClose}
          />
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <button
      {...buttonProps}
      onClick={onPress}
      onMouseEnter={(e) => {
        e.currentTarget.setAttribute('data-hover', 'true');
        onFocus();
      }}
      onMouseLeave={(e) => {
        e.currentTarget.removeAttribute('data-hover');
      }}
    >
      {content}
    </button>
  );
};
