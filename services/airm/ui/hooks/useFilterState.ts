// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { debounce, isEqual } from 'lodash';
import { FILTER_CONSTANTS } from '@/components/shared/Filters/FilterDropdown/constants';

import {
  FilterStateConfig,
  FilterStateResult,
} from '@/types/filter-dropdown/use-filter-state';

/**
 * Determines which item the user specifically interacted with during first selection.
 * Pure function extracted for clarity and testability.
 */
const determineUserFocusedItem = (
  newKeys: string[],
  currentKeys: Set<string>,
): string => {
  const newlySelectedKeys = newKeys.filter((key) => !currentKeys.has(key));
  const deselectedKeys = Array.from(currentKeys).filter(
    (key) => !newKeys.includes(key),
  );

  // Handle keyboard interaction - single item change
  if (newlySelectedKeys.length === 1) return newlySelectedKeys[0];
  if (deselectedKeys.length === 1) return deselectedKeys[0];

  return newKeys[0];
};

/**
 * Custom hook for managing filter state, including internal state,
 * external state synchronization, and user interaction tracking.
 *
 * @param config Configuration object for the hook
 * @returns State and handlers for managing filter selection
 */
export const useFilterState = ({
  selectedKeys,
  defaultSelectedKeys,
  items = [],
  onSelectionChange,
}: FilterStateConfig): FilterStateResult => {
  /**
   * Calculates effective default keys: use provided default or all item keys
   */
  const effectiveDefaultKeys = useMemo(
    () =>
      defaultSelectedKeys !== undefined
        ? defaultSelectedKeys
        : items.map((item) => item.key),
    [defaultSelectedKeys, items],
  );

  const [hasUserInteracted, setHasUserInteracted] = useState(false);
  const [internalSelectedKeys, setInternalSelectedKeys] = useState<string[]>(
    () =>
      selectedKeys && selectedKeys.length > 0
        ? [...selectedKeys]
        : [...effectiveDefaultKeys],
  );

  const isInternalUpdateRef = useRef(false);
  const isIntentionalResetRef = useRef(false);
  const lastExternalSelectedKeys = useRef<string[]>(selectedKeys || []);

  // Refs for stable callbacks - avoids recreating debounced function
  const onSelectionChangeRef = useRef(onSelectionChange);
  const effectiveDefaultKeysRef = useRef(effectiveDefaultKeys);
  const currentSelectedSetRef = useRef<Set<string>>(new Set());
  const hasUserInteractedRef = useRef(hasUserInteracted);

  /**
   * Set representation of current selection for efficient lookups
   */
  const currentSelectedSet = useMemo(
    () => new Set(internalSelectedKeys),
    [internalSelectedKeys],
  );

  // Keep refs in sync with latest values
  onSelectionChangeRef.current = onSelectionChange;
  effectiveDefaultKeysRef.current = effectiveDefaultKeys;
  currentSelectedSetRef.current = currentSelectedSet;
  hasUserInteractedRef.current = hasUserInteracted;

  const [debouncedSyncExternalFn] = useState(() =>
    debounce((keys: string[]) => {
      const keysToSync =
        keys.length || isIntentionalResetRef.current
          ? keys
          : effectiveDefaultKeysRef.current;

      lastExternalSelectedKeys.current = keysToSync.slice();
      isInternalUpdateRef.current = true;
      isIntentionalResetRef.current = false;

      onSelectionChangeRef.current?.(new Set(keysToSync));

      setTimeout(() => {
        isInternalUpdateRef.current = false;
      }, FILTER_CONSTANTS.STATE_SYNC_TIMEOUT);
    }, FILTER_CONSTANTS.DEBOUNCE_DELAY),
  );

  /**
   * Handles external state changes by updating internal state
   * @param newExternalKeys - New external keys to sync with
   */
  const handleExternalStateChange = useCallback(
    (newExternalKeys: string[]) => {
      setInternalSelectedKeys(newExternalKeys.slice());
      lastExternalSelectedKeys.current = newExternalKeys;

      const isBackToDefaults = isEqual(
        new Set(newExternalKeys),
        new Set(effectiveDefaultKeys),
      );

      if (isBackToDefaults) setHasUserInteracted(false);
    },
    [effectiveDefaultKeys],
  );

  /**
   * Updates internal state and schedules external sync
   * @param keys - Array of selected keys to update
   */
  const updateInternalSelection = useCallback(
    (keys: string[]) => {
      setInternalSelectedKeys(keys);
      debouncedSyncExternalFn(keys);
    },
    [debouncedSyncExternalFn],
  );

  /**
   * Resets the selection to default values
   */
  const handleReset = useCallback(() => {
    const defaultKeys = effectiveDefaultKeysRef.current.slice();
    setInternalSelectedKeys(defaultKeys);
    debouncedSyncExternalFn.cancel();
    isIntentionalResetRef.current = true;
    lastExternalSelectedKeys.current = defaultKeys;
    debouncedSyncExternalFn(defaultKeys);
    setHasUserInteracted(false);
  }, [debouncedSyncExternalFn]);

  /**
   * Handles selection changes from the dropdown component with determining selection:
   * - first interaction uses focused item
   * - subsequent use full selection
   * Uses refs for hasUserInteracted and currentSelectedSet to maintain stable reference.
   * @param keys - The new selection from the dropdown (can be Set or Array)
   */
  const handleSelectionChange = useCallback(
    (keys: Set<string> | string[]) => {
      const newKeysArray = Array.from(keys) as string[];

      // If selection is empty, reset to defaults
      if (!newKeysArray.length) return handleReset();

      const keysToSelect = !hasUserInteractedRef.current
        ? [
            determineUserFocusedItem(
              newKeysArray,
              currentSelectedSetRef.current,
            ),
          ]
        : newKeysArray;

      updateInternalSelection(keysToSelect);
      setHasUserInteracted(true);
    },
    [handleReset, updateInternalSelection],
  );

  /**
   * Handles external state synchronization
   */
  useEffect(() => {
    const currentExternal = selectedKeys || [];
    const isExternalChange = !isEqual(
      currentExternal,
      lastExternalSelectedKeys.current,
    );
    const isNotInternalUpdate = !isInternalUpdateRef.current;

    if (isExternalChange && isNotInternalUpdate) {
      handleExternalStateChange(currentExternal);
    }
  }, [selectedKeys, handleExternalStateChange]);

  /**
   * Syncs when effectiveDefaultKeys change
   */
  useEffect(() => {
    const hasNoExternalSelection = !selectedKeys?.length;
    const hasDefaults = effectiveDefaultKeys.length > 0;

    const shouldApplyDefaults =
      hasNoExternalSelection && hasDefaults && !hasUserInteracted;

    if (shouldApplyDefaults)
      setInternalSelectedKeys(effectiveDefaultKeys.slice());
  }, [effectiveDefaultKeys, selectedKeys, hasUserInteracted]);

  /**
   * Cleanup effect to cancel debounced function on unmount
   */
  useEffect(() => {
    return () => {
      debouncedSyncExternalFn.cancel();
    };
  }, [debouncedSyncExternalFn]);

  return {
    currentSelectedSet,
    hasUserInteracted,
    handleSelectionChange,
    handleReset,
  };
};
