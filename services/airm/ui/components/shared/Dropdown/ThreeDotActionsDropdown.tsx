// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  Button,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Tooltip,
} from '@heroui/react';
import {
  IconAlertTriangle,
  IconCircleX,
  IconDotsVertical,
  IconInfoCircle,
} from '@tabler/icons-react';
import { Key } from 'react';

import { ActionItem } from '@/types/data-table/clientside-table';
import { ActionFieldHintType } from '@/types/enums/data-table';

interface ThreeDotActionsDropdownProps<T> {
  actions: ActionItem<T>[];
  item: T;
}

const handleDropdownItemAction =
  <T,>(actions: ActionItem<T>[], item: T) =>
  (dropdownItemKey: Key) => {
    const action = actions.find((action) => action.key === dropdownItemKey);
    if (action) action.onPress(item);
  };

const getDisabledKeys = <T,>(actions: ActionItem<T>[], item: T): string[] => {
  const disabledKeys = new Set();
  actions.forEach((action) => {
    if (typeof action?.isDisabled === 'function') {
      if (action.isDisabled(item)) disabledKeys.add(action.key);
    } else if (action?.isDisabled) {
      disabledKeys.add(action.key);
    }
  });

  return Array.from(disabledKeys) as string[];
};

const ThreeDotActionsDropdown = <T,>({
  actions,
  item,
}: ThreeDotActionsDropdownProps<T>) => {
  if (actions.length === 0) {
    return null;
  }

  const hints = actions.flatMap(
    (action) => action.hint?.filter((h) => h.showHint(item)) ?? [],
  );
  const hasHints = hints.length > 0;

  const hintJsx =
    hints && hints.length > 0 ? (
      <div className="flex flex-col gap-1 mt-1 text-xs">
        {hints.map((h) => (
          <div className="flex items-center gap-1" key={h?.message}>
            {h?.type === ActionFieldHintType.INFO && (
              <IconInfoCircle className="text-info-500" />
            )}
            {h?.type === ActionFieldHintType.WARNING && (
              <IconAlertTriangle className="text-warning-500" />
            )}
            {h?.type === ActionFieldHintType.ERROR && (
              <IconCircleX className="text-error-500" />
            )}
            <span>{h?.message}</span>
          </div>
        ))}
      </div>
    ) : null;

  const DropDownMenu = (
    <DropdownMenu
      onAction={handleDropdownItemAction(actions, item)}
      disabledKeys={getDisabledKeys(actions, item)}
    >
      {actions.map((action) => (
        <DropdownItem
          className={[
            action.className,
            action?.color !== 'default' ? ` text-${action.color}` : '',
          ].join(' ')}
          key={action.key}
          aria-label={action.label}
          data-testid={action.key}
          startContent={action.startContent}
        >
          {action.label}
        </DropdownItem>
      ))}
    </DropdownMenu>
  );

  return (
    <div className="relative flex justify-center items-center gap-2">
      <Dropdown>
        <DropdownTrigger>
          <Button
            isIconOnly
            size="sm"
            variant="light"
            aria-label="list.actions.label"
            className="h-auto w-6 min-w-6"
          >
            <IconDotsVertical className="text-default-300" />
          </Button>
        </DropdownTrigger>
        {hasHints ? (
          <Tooltip content={hintJsx}>{DropDownMenu}</Tooltip>
        ) : (
          DropDownMenu
        )}
      </Dropdown>
    </div>
  );
};

export default ThreeDotActionsDropdown;
