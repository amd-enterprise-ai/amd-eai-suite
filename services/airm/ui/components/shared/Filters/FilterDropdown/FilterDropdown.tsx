// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSection,
  Selection,
} from '@heroui/react';
import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useMemo,
  ReactNode,
} from 'react';

import FilterButtonTrigger from './FilterButtonTrigger';
import { FILTER_CONSTANTS } from './constants';
import { useFilterState } from '@/hooks/useFilterState';
import type { FilterItem } from '@/types/filter-dropdown/use-filter-state';

export type { FilterItem };

/**
 * Ref interface for FilterDropdown component
 */
export interface FilterDropdownRef {
  clear: () => void;
}

/**
 * Props for the FilterDropdown component
 */
export interface FilterDropdownProps {
  label: string;
  items: FilterItem[];
  icon?: ReactNode;
  className?: string;
  defaultSelectedKeys?: string[];
  selectedKeys?: string[];
  showDescription?: boolean;
  onSelectionChange?: (keys: Set<string>) => void;
  tooltipText?: string;
}

/**
 * FilterDropdown Component
 *
 * A multi-select dropdown with advanced features including:
 * - External state synchronization with debouncing
 * - First-selection behavior (clear all, select one)
 * - Reset functionality
 * - Accessible keyboard navigation
 *
 * @example
 * ```tsx
 * <FilterDropdown
 *   label="Status"
 *   items={statusItems}
 *   selectedKeys={selectedStatuses}
 *   onSelectionChange={setSelectedStatuses}
 *   defaultSelectedKeys={['active']}
 * />
 * ```
 */
const FilterDropdown = forwardRef<FilterDropdownRef, FilterDropdownProps>(
  (
    {
      label,
      items,
      icon,
      className,
      showDescription = true,
      tooltipText,
      selectedKeys,
      defaultSelectedKeys,
      onSelectionChange,
    },
    ref,
  ) => {
    const {
      currentSelectedSet,
      hasUserInteracted,
      handleSelectionChange,
      handleReset,
    } = useFilterState({
      selectedKeys,
      defaultSelectedKeys,
      items,
      onSelectionChange,
    });

    useImperativeHandle(ref, () => ({ clear: handleReset }), [handleReset]);

    const tooltip = useMemo(() => {
      if (tooltipText) return tooltipText;
      return items
        .filter((item) => currentSelectedSet.has(item.key))
        .map((item) => item.label)
        .join(', ');
    }, [items, currentSelectedSet, tooltipText]);

    const handleDropdownSelectionChange = useCallback(
      (keys: Selection) => {
        handleSelectionChange(new Set(Array.from(keys).map(String)));
      },
      [handleSelectionChange],
    );

    const itemClassNames = useMemo(
      () => ({
        selectedIcon: !hasUserInteracted ? 'opacity-30' : '',
      }),
      [hasUserInteracted],
    );

    const dropdownItems = useMemo(
      () =>
        items.map(
          ({
            key,
            label: itemLabel,
            description = '',
            showDivider = false,
          }) => (
            <DropdownItem
              key={key}
              className="capitalize"
              aria-label={itemLabel}
              description={showDescription ? description : undefined}
              showDivider={showDivider}
              classNames={itemClassNames}
            >
              {itemLabel}
            </DropdownItem>
          ),
        ),
      [items, showDescription, itemClassNames],
    );

    return (
      <Dropdown className={FILTER_CONSTANTS.MIN_DROPDOWN_WIDTH}>
        <FilterButtonTrigger
          label={label}
          startContent={icon}
          className={className}
          tooltipText={tooltip}
          numberOfSelectedKeys={currentSelectedSet.size}
          isActive={hasUserInteracted}
          onReset={handleReset}
        />
        <DropdownMenu
          aria-label={label}
          closeOnSelect={false}
          selectedKeys={currentSelectedSet}
          selectionMode="multiple"
          onSelectionChange={handleDropdownSelectionChange}
        >
          <DropdownSection>{dropdownItems}</DropdownSection>
        </DropdownMenu>
      </Dropdown>
    );
  },
);

FilterDropdown.displayName = 'FilterDropdown';

export default FilterDropdown;
