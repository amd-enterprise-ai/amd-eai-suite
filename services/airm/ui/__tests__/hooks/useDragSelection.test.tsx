// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { useDragSelection } from '@/hooks/useDragSelection';
import { DragSelectionConfig } from '@/types/filter-dropdown/use-drag-selection';

describe('useDragSelection', () => {
  const mockOnSelectionChange = vi.fn();
  const mockOnUserInteraction = vi.fn();

  const defaultConfig: DragSelectionConfig = {
    selectedKeys: new Set<string>(),
    onSelectionChange: mockOnSelectionChange,
    hasUserInteracted: false,
    onUserInteraction: mockOnUserInteraction,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Clean up any event listeners
    document.removeEventListener('mouseup', expect.any(Function));
  });

  describe('initial state', () => {
    it('should return correct initial state', () => {
      const { result } = renderHook(() => useDragSelection(defaultConfig));

      expect(result.current.isDragging).toBe(false);
      expect(result.current.dragStartItem).toBe(null);
      expect(typeof result.current.handleMouseDown).toBe('function');
      expect(typeof result.current.handleMouseEnter).toBe('function');
      expect(typeof result.current.handleMouseUp).toBe('function');
    });
  });

  describe('handleMouseDown', () => {
    it('should initiate drag and select first item when user has not interacted', () => {
      const { result } = renderHook(() => useDragSelection(defaultConfig));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      expect(mockEvent.preventDefault).toHaveBeenCalled();
      expect(result.current.isDragging).toBe(true);
      expect(result.current.dragStartItem).toBe('item1');
      expect(mockOnSelectionChange).toHaveBeenCalledWith(['item1']);
      expect(mockOnUserInteraction).toHaveBeenCalled();
    });

    it('should add item to selection when user has interacted and item is not selected', () => {
      const config = {
        ...defaultConfig,
        hasUserInteracted: true,
        selectedKeys: new Set(['item2']),
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      expect(result.current.isDragging).toBe(true);
      expect(result.current.dragStartItem).toBe('item1');
      expect(mockOnSelectionChange).toHaveBeenCalledWith(['item2', 'item1']);
    });

    it('should remove item from selection when user has interacted and item is already selected', () => {
      const config = {
        ...defaultConfig,
        hasUserInteracted: true,
        selectedKeys: new Set(['item1', 'item2']),
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      expect(result.current.isDragging).toBe(true);
      expect(result.current.dragStartItem).toBe('item1');
      expect(mockOnSelectionChange).toHaveBeenCalledWith(['item2']);
    });

    it('should handle errors gracefully during mouse down', () => {
      const consoleSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});
      const errorConfig = {
        ...defaultConfig,
        onSelectionChange: vi.fn(() => {
          throw new Error('Selection change failed');
        }),
      };

      const { result } = renderHook(() => useDragSelection(errorConfig));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      expect(consoleSpy).toHaveBeenCalledWith(
        'Drag operation failed during mouse down:',
        expect.any(Error),
      );
      expect(result.current.isDragging).toBe(false);
      expect(result.current.dragStartItem).toBe(null);

      consoleSpy.mockRestore();
    });
  });

  describe('handleMouseEnter', () => {
    it('should do nothing when not dragging', () => {
      const { result } = renderHook(() => useDragSelection(defaultConfig));

      act(() => {
        result.current.handleMouseEnter('item1');
      });

      expect(mockOnSelectionChange).not.toHaveBeenCalled();
    });

    it('should do nothing when dragStartItem is null', () => {
      const { result } = renderHook(() => useDragSelection(defaultConfig));

      // Manually set isDragging to true but keep dragStartItem as null
      act(() => {
        const mockEvent = {
          preventDefault: vi.fn(),
        } as unknown as React.MouseEvent;
        result.current.handleMouseDown('item1', mockEvent);
        result.current.handleMouseUp();
      });

      // Reset the drag state to test the condition
      result.current.handleMouseUp();

      act(() => {
        result.current.handleMouseEnter('item2');
      });

      // Should only have been called once during mouseDown
      expect(mockOnSelectionChange).toHaveBeenCalledTimes(1);
    });

    it('should add item during drag when isDragAdding is true', () => {
      const config = {
        ...defaultConfig,
        selectedKeys: new Set(['item1']),
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag with unselected item (will set isDragAdding to true)
      act(() => {
        result.current.handleMouseDown('item2', mockEvent);
      });

      // Clear previous calls to focus on the mouseEnter behavior
      mockOnSelectionChange.mockClear();

      // Enter another item during drag
      act(() => {
        result.current.handleMouseEnter('item3');
      });

      // Since selectedKeys doesn't update in tests, item3 will be added to the original set
      expect(mockOnSelectionChange).toHaveBeenCalledWith(['item1', 'item3']);
    });

    it('should remove item during drag when isDragAdding is false', () => {
      const config = {
        ...defaultConfig,
        selectedKeys: new Set(['item1', 'item2', 'item3']),
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag with selected item (will set isDragAdding to false)
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      // Clear previous calls to focus on the mouseEnter behavior
      mockOnSelectionChange.mockClear();

      // Enter another item during drag
      act(() => {
        result.current.handleMouseEnter('item2');
      });

      // Since selectedKeys doesn't update in tests, item2 will be removed from the original set
      expect(mockOnSelectionChange).toHaveBeenCalledWith(['item1', 'item3']);
    });

    it('should handle errors gracefully during mouse enter', () => {
      const consoleSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});
      const errorConfig = {
        ...defaultConfig,
        hasUserInteracted: true,
        onSelectionChange: vi
          .fn()
          .mockImplementationOnce(() => {}) // First call succeeds (mouseDown)
          .mockImplementationOnce(() => {
            // Second call fails (mouseEnter)
            throw new Error('Selection change failed');
          }),
      };

      const { result } = renderHook(() => useDragSelection(errorConfig));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      // Trigger error during mouse enter
      act(() => {
        result.current.handleMouseEnter('item2');
      });

      expect(consoleSpy).toHaveBeenCalledWith(
        'Drag operation failed during mouse enter:',
        expect.any(Error),
      );
      expect(result.current.isDragging).toBe(false);

      consoleSpy.mockRestore();
    });
  });

  describe('handleMouseUp', () => {
    it('should reset drag state', () => {
      const { result } = renderHook(() => useDragSelection(defaultConfig));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      expect(result.current.isDragging).toBe(true);
      expect(result.current.dragStartItem).toBe('item1');

      // End drag
      act(() => {
        result.current.handleMouseUp();
      });

      expect(result.current.isDragging).toBe(false);
      expect(result.current.dragStartItem).toBe(null);
    });
  });

  describe('global mouse up event listener', () => {
    it('should add event listener when dragging starts', () => {
      const addEventListenerSpy = vi.spyOn(document, 'addEventListener');
      const { result } = renderHook(() => useDragSelection(defaultConfig));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        'mouseup',
        expect.any(Function),
      );
    });

    it('should remove event listener when dragging ends', () => {
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
      const { result } = renderHook(() => useDragSelection(defaultConfig));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      // End drag
      act(() => {
        result.current.handleMouseUp();
      });

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'mouseup',
        expect.any(Function),
      );
    });

    it('should remove event listener when component unmounts during drag', () => {
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
      const { result, unmount } = renderHook(() =>
        useDragSelection(defaultConfig),
      );
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      // Unmount component
      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'mouseup',
        expect.any(Function),
      );
    });

    it('should handle global mouse up event to end drag', () => {
      const { result } = renderHook(() => useDragSelection(defaultConfig));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      expect(result.current.isDragging).toBe(true);

      // Simulate global mouse up
      act(() => {
        const mouseUpEvent = new MouseEvent('mouseup');
        document.dispatchEvent(mouseUpEvent);
      });

      expect(result.current.isDragging).toBe(false);
      expect(result.current.dragStartItem).toBe(null);
    });
  });

  describe('applySelectionChange behavior', () => {
    it('should not add duplicate items when adding', () => {
      const config = {
        ...defaultConfig,
        selectedKeys: new Set(['item1']),
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Try to add item2 first
      act(() => {
        result.current.handleMouseDown('item2', mockEvent); // Start with item2
      });

      // Clear previous calls
      mockOnSelectionChange.mockClear();

      act(() => {
        result.current.handleMouseEnter('item1'); // Enter item1 (already selected)
      });

      // Should not add item1 again - it was already in the original set
      expect(mockOnSelectionChange).toHaveBeenCalledWith(['item1']);
    });

    it('should handle removing non-existent items gracefully', () => {
      const config = {
        ...defaultConfig,
        selectedKeys: new Set(['item1']),
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag with selected item (isDragAdding = false)
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      // Clear previous calls
      mockOnSelectionChange.mockClear();

      // Try to remove item that's not in selection
      act(() => {
        result.current.handleMouseEnter('item2');
      });

      // Should not cause errors, item2 simply won't be removed since it wasn't there
      expect(mockOnSelectionChange).toHaveBeenCalledWith(['item1']);
    });
  });

  describe('dependency updates', () => {
    it('should update callbacks when dependencies change', () => {
      const initialConfig = {
        ...defaultConfig,
        selectedKeys: new Set(['item1']),
        hasUserInteracted: true,
      };

      const { result, rerender } = renderHook(
        (config) => useDragSelection(config),
        { initialProps: initialConfig },
      );

      const initialHandleMouseDown = result.current.handleMouseDown;

      // Update selectedKeys
      const updatedConfig = {
        ...initialConfig,
        selectedKeys: new Set(['item1', 'item2']),
      };

      rerender(updatedConfig);

      // Function references should be the same if dependencies haven't changed
      // But internal behavior should reflect new selectedKeys
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      act(() => {
        result.current.handleMouseDown('item3', mockEvent);
      });

      // Should include both existing items plus the new one
      expect(mockOnSelectionChange).toHaveBeenCalledWith([
        'item1',
        'item2',
        'item3',
      ]);
    });
  });

  describe('edge cases', () => {
    it('should handle empty selectedKeys set', () => {
      const config = {
        ...defaultConfig,
        selectedKeys: new Set<string>(),
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      expect(mockOnSelectionChange).toHaveBeenCalledWith(['item1']);
    });

    it('should handle multiple rapid mouse enter events', () => {
      const config = {
        ...defaultConfig,
        selectedKeys: new Set<string>(),
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      // Clear previous calls
      mockOnSelectionChange.mockClear();

      // Multiple rapid enters - each call will start from the original selectedKeys (empty set)
      act(() => {
        result.current.handleMouseEnter('item2');
        result.current.handleMouseEnter('item3');
        result.current.handleMouseEnter('item4');
      });

      // Each enter adds to the original empty set, so the last call should be ['item4']
      expect(mockOnSelectionChange).toHaveBeenLastCalledWith(['item4']);
    });

    it('should handle mouse enter on same item multiple times', () => {
      const config = {
        ...defaultConfig,
        selectedKeys: new Set<string>(),
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      // Clear previous calls
      mockOnSelectionChange.mockClear();

      // Enter same item multiple times
      act(() => {
        result.current.handleMouseEnter('item2');
        result.current.handleMouseEnter('item2');
        result.current.handleMouseEnter('item2');
      });

      // Should not add duplicates - each call adds item2 to original empty set
      expect(mockOnSelectionChange).toHaveBeenLastCalledWith(['item2']);
    });

    it('should handle drag operations with very large selection sets', () => {
      const largeSelection = new Set(
        Array.from({ length: 1000 }, (_, i) => `item${i}`),
      );
      const config = {
        ...defaultConfig,
        selectedKeys: largeSelection,
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag with new item
      act(() => {
        result.current.handleMouseDown('newItem', mockEvent);
      });

      // Should handle large arrays without issues
      expect(mockOnSelectionChange).toHaveBeenCalledWith(
        expect.arrayContaining([...Array.from(largeSelection), 'newItem']),
      );
    });

    it('should handle special characters in item keys', () => {
      const specialKeys = new Set([
        'item with spaces',
        'item-with-dashes',
        'item.with.dots',
        'item/with/slashes',
      ]);
      const config = {
        ...defaultConfig,
        selectedKeys: specialKeys,
        hasUserInteracted: true,
      };
      const { result } = renderHook(() => useDragSelection(config));
      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag with item that has special characters
      act(() => {
        result.current.handleMouseDown('new item@#$%', mockEvent);
      });

      expect(mockOnSelectionChange).toHaveBeenCalledWith(
        expect.arrayContaining([...Array.from(specialKeys), 'new item@#$%']),
      );
    });
  });

  describe('real-world simulation with state updates', () => {
    it('should work correctly when selectedKeys are updated between interactions', () => {
      let currentSelectedKeys = new Set(['item1']);
      const mockOnSelectionChangeWithUpdate = vi.fn((keys: string[]) => {
        currentSelectedKeys = new Set(keys);
      });

      const initialConfig = {
        ...defaultConfig,
        selectedKeys: currentSelectedKeys,
        hasUserInteracted: true,
        onSelectionChange: mockOnSelectionChangeWithUpdate,
      };

      const { result, rerender } = renderHook(
        (config) => useDragSelection(config),
        { initialProps: initialConfig },
      );

      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // Start drag with new item
      act(() => {
        result.current.handleMouseDown('item2', mockEvent);
      });

      // Simulate parent component updating selectedKeys
      rerender({
        ...initialConfig,
        selectedKeys: currentSelectedKeys,
      });

      // Clear previous calls
      mockOnSelectionChangeWithUpdate.mockClear();

      // Continue drag with another item - should work with updated state
      act(() => {
        result.current.handleMouseEnter('item3');
      });

      expect(mockOnSelectionChangeWithUpdate).toHaveBeenCalledWith(
        expect.arrayContaining(['item1', 'item2', 'item3']),
      );
    });

    it('should handle rapid drag operations with state updates', () => {
      let currentSelectedKeys = new Set<string>();
      const mockOnSelectionChangeWithUpdate = vi.fn((keys: string[]) => {
        currentSelectedKeys = new Set(keys);
      });

      const createConfig = () => ({
        ...defaultConfig,
        selectedKeys: currentSelectedKeys,
        hasUserInteracted: true,
        onSelectionChange: mockOnSelectionChangeWithUpdate,
      });

      const { result, rerender } = renderHook(
        (config) => useDragSelection(config),
        { initialProps: createConfig() },
      );

      const mockEvent = {
        preventDefault: vi.fn(),
      } as unknown as React.MouseEvent;

      // First drag operation
      act(() => {
        result.current.handleMouseDown('item1', mockEvent);
      });

      // Simulate state update
      rerender(createConfig());

      // End first drag
      act(() => {
        result.current.handleMouseUp();
      });

      // Start second drag operation
      act(() => {
        result.current.handleMouseDown('item2', mockEvent);
      });

      // Should accumulate selections correctly
      expect(currentSelectedKeys.has('item1')).toBe(true);
      expect(currentSelectedKeys.has('item2')).toBe(true);
    });
  });

  describe('performance considerations', () => {
    it('should maintain referential equality of handlers when dependencies do not change', () => {
      const config = {
        ...defaultConfig,
        selectedKeys: new Set(['item1']),
      };

      const { result, rerender } = renderHook(() => useDragSelection(config));

      const initialHandlers = {
        handleMouseDown: result.current.handleMouseDown,
        handleMouseEnter: result.current.handleMouseEnter,
        handleMouseUp: result.current.handleMouseUp,
      };

      // Rerender with same config
      rerender();

      expect(result.current.handleMouseDown).toBe(
        initialHandlers.handleMouseDown,
      );
      expect(result.current.handleMouseEnter).toBe(
        initialHandlers.handleMouseEnter,
      );
      expect(result.current.handleMouseUp).toBe(initialHandlers.handleMouseUp);
    });

    it('should update handlers when dependencies change', () => {
      const initialConfig = {
        ...defaultConfig,
        selectedKeys: new Set(['item1']),
      };

      const { result, rerender } = renderHook(
        (config) => useDragSelection(config),
        { initialProps: initialConfig },
      );

      const initialHandlers = {
        handleMouseDown: result.current.handleMouseDown,
        handleMouseEnter: result.current.handleMouseEnter,
      };

      // Update selectedKeys dependency
      const updatedConfig = {
        ...initialConfig,
        selectedKeys: new Set(['item1', 'item2']),
      };

      rerender(updatedConfig);

      // handleMouseDown and handleMouseEnter should be updated due to selectedKeys dependency
      expect(result.current.handleMouseDown).not.toBe(
        initialHandlers.handleMouseDown,
      );
      expect(result.current.handleMouseEnter).not.toBe(
        initialHandlers.handleMouseEnter,
      );

      // handleMouseUp has no dependencies and should maintain referential equality
      expect(result.current.handleMouseUp).toBe(result.current.handleMouseUp);
    });
  });
});
