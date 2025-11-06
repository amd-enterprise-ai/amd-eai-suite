// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useState } from 'react';
import {
  DragSelectionConfig,
  DragSelectionResult,
} from '@/types/filter-dropdown/use-drag-selection';

/**
 * Custom hook for managing drag selection functionality in the FilterDropdown.
 * Handles mouse-based drag operations for multi-selecting items.
 *
 * @returns Drag state and event handlers
 */
export const useDragSelection = ({
  selectedKeys,
  onSelectionChange,
  hasUserInteracted,
  onUserInteraction,
}: DragSelectionConfig): DragSelectionResult => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartItem, setDragStartItem] = useState<string | null>(null);
  const [isDragAdding, setIsDragAdding] = useState(true);

  /**
   * Helper function to apply selection change based on drag operation.
   *
   * @param itemKey - The key of the item to add or remove from selection
   * @param isAdding - Whether to add (true) or remove (false) the item
   */
  const applySelectionChange = useCallback(
    (itemKey: string, isAdding: boolean) => {
      const newSelectionArray = Array.from(selectedKeys);

      if (isAdding) {
        if (!selectedKeys.has(itemKey)) newSelectionArray.push(itemKey);
      } else {
        const index = newSelectionArray.indexOf(itemKey);
        if (index > -1) newSelectionArray.splice(index, 1);
      }

      onSelectionChange(newSelectionArray);
    },
    [selectedKeys, onSelectionChange],
  );

  /**
   * Handles mouse down events on dropdown items.
   * Initiates drag selection and applies first-click behavior.
   *
   * @param itemKey - The unique identifier of the item being clicked
   * @param event - The mouse event from the dropdown item
   */
  const handleMouseDown = useCallback(
    (itemKey: string, event: React.MouseEvent) => {
      try {
        event.preventDefault();
        setIsDragging(true);
        setDragStartItem(itemKey);

        if (!hasUserInteracted) {
          onSelectionChange([itemKey]);
          onUserInteraction();
          setIsDragAdding(true);
        } else {
          const isAdding = !selectedKeys.has(itemKey);
          applySelectionChange(itemKey, isAdding);
          setIsDragAdding(isAdding);
        }
      } catch (error) {
        console.error('Drag operation failed during mouse down:', error);
        setIsDragging(false);
        setDragStartItem(null);
      }
    },
    [
      selectedKeys,
      hasUserInteracted,
      onUserInteraction,
      onSelectionChange,
      applySelectionChange,
    ],
  );

  /**
   * Handles mouse enter events during drag operations.
   * Applies drag state to items being dragged over.
   *
   * @param itemKey - The unique identifier of the item being entered
   */
  const handleMouseEnter = useCallback(
    (itemKey: string) => {
      if (!isDragging || !dragStartItem) return;

      try {
        applySelectionChange(itemKey, isDragAdding);
      } catch (error) {
        console.error('Drag operation failed during mouse enter:', error);
        setIsDragging(false);
      }
    },
    [isDragging, dragStartItem, isDragAdding, applySelectionChange],
  );

  /**
   * Handles mouse up events to end drag operations.
   * Terminates the current drag session by resetting drag state.
   */
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragStartItem(null);
  }, []);

  /**
   * Global mouse up listener to handle mouse up events outside the dropdown.
   * This ensures drag operations are properly terminated even if the user
   * releases the mouse outside the component boundaries.
   */
  useEffect(() => {
    if (!isDragging) return;

    document.addEventListener('mouseup', handleMouseUp);
    return () => document.removeEventListener('mouseup', handleMouseUp);
  }, [isDragging, handleMouseUp]);

  return {
    isDragging,
    dragStartItem,
    handleMouseDown,
    handleMouseEnter,
    handleMouseUp,
  };
};
