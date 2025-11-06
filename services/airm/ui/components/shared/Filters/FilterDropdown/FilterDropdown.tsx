// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSection,
} from '@heroui/react';
import { forwardRef, useImperativeHandle, useMemo, ReactNode } from 'react';

import FilterButtonTrigger from './FilterButtonTrigger';
import { DROPDOWN_ITEM_STYLES, FILTER_CONSTANTS } from './constants';
import { useDragSelection } from '@/hooks/useDragSelection';
import { useFilterState } from '@/hooks/useFilterState';

/**
 * Represents a single filter item in the dropdown
 */
export interface FilterItem {
  key: string;
  label: string;
  description?: string;
  showDivider?: boolean;
}

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
 * A sophisticated multi-select dropdown with advanced features including:
 * - Drag selection for efficient multi-item selection
 * - External state synchronization with debouncing
 * - First-selection behavior (clear all, select one)
 * - Reset functionality
 * - Accessible keyboard navigation
 *
 * The component is architected using the separation of concerns principle:
 * - useFilterState: Manages internal state and external synchronization
 * - useDragSelection: Handles drag interaction logic
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
    // Extract state management logic
    const filterStateProps = useFilterState({
      selectedKeys,
      defaultSelectedKeys,
      items,
      onSelectionChange,
    });

    // Extract drag selection logic
    const dragProps = useDragSelection({
      selectedKeys: filterStateProps.currentSelectedSet,
      onSelectionChange: (keys) =>
        filterStateProps.handleSelectionChange(new Set(keys)),
      hasUserInteracted: filterStateProps.hasUserInteracted,
      onUserInteraction: filterStateProps.onUserInteraction,
    });

    // Expose clear function via ref for external control
    useImperativeHandle(
      ref,
      () => ({
        clear: filterStateProps.handleReset,
      }),
      [filterStateProps.handleReset],
    );

    /**
     * Generate tooltip text based on selected items or custom text.
     * Memoized for performance to avoid recalculation on every render.
     */
    const tooltip = useMemo(() => {
      if (tooltipText) return tooltipText;

      return items
        .filter((item) => filterStateProps.currentSelectedSet.has(item.key))
        .map((item) => item.label)
        .join(', ');
    }, [items, filterStateProps.currentSelectedSet, tooltipText]);

    return (
      <Dropdown className={FILTER_CONSTANTS.MIN_DROPDOWN_WIDTH}>
        <FilterButtonTrigger
          label={label}
          startContent={icon}
          className={className}
          tooltipText={tooltip}
          numberOfSelectedKeys={filterStateProps.currentSelectedSet.size}
          isActive={filterStateProps.hasUserInteracted}
          onReset={filterStateProps.handleReset}
        />
        <DropdownMenu
          aria-label={label}
          closeOnSelect={false}
          selectedKeys={
            filterStateProps.internalSelectedKeys as Iterable<string>
          }
          selectionMode="multiple"
          onSelectionChange={
            dragProps.isDragging
              ? undefined
              : (keys) =>
                  filterStateProps.handleSelectionChange(
                    Array.from(keys).map(String),
                  )
          }
        >
          <DropdownSection>
            {items.map(
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
                  classNames={{
                    selectedIcon: !filterStateProps.hasUserInteracted
                      ? 'opacity-30'
                      : '',
                  }}
                  onMouseDown={(event) => dragProps.handleMouseDown(key, event)}
                  onMouseEnter={() => dragProps.handleMouseEnter(key)}
                  onMouseUp={dragProps.handleMouseUp}
                  style={DROPDOWN_ITEM_STYLES}
                >
                  {itemLabel}
                </DropdownItem>
              ),
            )}
          </DropdownSection>
        </DropdownMenu>
      </Dropdown>
    );
  },
);

FilterDropdown.displayName = 'FilterDropdown';

export default FilterDropdown;
