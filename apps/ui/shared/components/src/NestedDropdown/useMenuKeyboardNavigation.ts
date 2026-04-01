// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  canExecuteAction,
  FlattenedDropdownItem,
  hasNestedActions,
  isActionDisabled,
  isSectionHeader,
} from './utils';

interface UseMenuKeyboardNavigationOptions {
  actions: FlattenedDropdownItem[];
  onClose: () => void;
  onRequestClose?: () => void;
  isRootLevel: boolean;
}

interface UseMenuKeyboardNavigationReturn {
  focusedIndex: number;
  openKey: string | null;
  setOpenKey: (key: string | null) => void;
  setFocusedIndex: (index: number) => void;
  handleKeyDown: (e: React.KeyboardEvent) => void;
}

export const useMenuKeyboardNavigation = ({
  actions,
  onClose,
  onRequestClose,
  isRootLevel,
}: UseMenuKeyboardNavigationOptions): UseMenuKeyboardNavigationReturn => {
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number>(0);
  const initializedRef = useRef(false);

  const isItemNavigable = useCallback(
    (action: FlattenedDropdownItem): boolean => {
      return !isSectionHeader(action) && !isActionDisabled(action);
    },
    [],
  );

  const findNextEnabledIndex = useCallback(
    (currentIndex: number, direction: 1 | -1): number => {
      let nextIndex = currentIndex + direction;
      while (nextIndex >= 0 && nextIndex < actions.length) {
        if (isItemNavigable(actions[nextIndex])) return nextIndex;
        nextIndex += direction;
      }
      return currentIndex;
    },
    [actions, isItemNavigable],
  );

  const findFirstEnabledIndex = useCallback((): number => {
    for (let i = 0; i < actions.length; i++) {
      if (isItemNavigable(actions[i])) return i;
    }
    return -1;
  }, [actions, isItemNavigable]);

  useEffect(() => {
    if (!initializedRef.current) {
      setFocusedIndex(findFirstEnabledIndex());
      initializedRef.current = true;
    }
  }, [findFirstEnabledIndex]);

  const executeAction = useCallback(
    (action: FlattenedDropdownItem) => {
      if (canExecuteAction(action)) {
        action.onPress();
        onClose();
      }
    },
    [onClose],
  );

  const handleClose = useCallback(() => {
    if (isRootLevel) {
      onClose();
    } else {
      onRequestClose?.();
    }
  }, [isRootLevel, onClose, onRequestClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (focusedIndex < 0) {
        if (e.key === 'Escape') {
          e.preventDefault();
          e.stopPropagation();
          handleClose();
        }
        return;
      }

      const focusedAction = actions[focusedIndex];
      const hasNested = hasNestedActions(focusedAction);

      const keyHandlers: Record<string, () => void> = {
        ArrowDown: () => {
          setFocusedIndex(findNextEnabledIndex(focusedIndex, 1));
        },
        ArrowUp: () => {
          setFocusedIndex(findNextEnabledIndex(focusedIndex, -1));
        },
        ' ': () => {
          if (hasNested) {
            setOpenKey(focusedAction.key);
          } else {
            executeAction(focusedAction);
          }
        },
        Enter: () => {
          if (hasNested) {
            setOpenKey(focusedAction.key);
          } else {
            executeAction(focusedAction);
          }
        },
        ArrowRight: () => {
          if (hasNested) {
            setOpenKey(focusedAction.key);
          }
        },
        Escape: handleClose,
        ArrowLeft: () => {
          if (!isRootLevel) {
            onRequestClose?.();
          }
        },
      };

      const handler = keyHandlers[e.key];
      if (handler) {
        e.preventDefault();
        e.stopPropagation();
        handler();
      }
    },
    [
      actions,
      focusedIndex,
      findNextEnabledIndex,
      executeAction,
      handleClose,
      isRootLevel,
      onRequestClose,
    ],
  );

  return {
    focusedIndex,
    openKey,
    setOpenKey,
    setFocusedIndex,
    handleKeyDown,
  };
};
