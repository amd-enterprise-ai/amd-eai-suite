// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  getStorageItem,
  setStorageItem,
  watchStorageItem,
} from '@/utils/app/storage';

import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// Mock addEventListener/removeEventListener
const addEventListenerMock = vi.fn();
const removeEventListenerMock = vi.fn();

Object.defineProperty(window, 'addEventListener', {
  value: addEventListenerMock,
  writable: true,
});

Object.defineProperty(window, 'removeEventListener', {
  value: removeEventListenerMock,
  writable: true,
});

describe('storage utils', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getStorageItem', () => {
    it('should return parsed JSON value when item exists', () => {
      const testValue = { key: 'value', number: 42 };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(testValue));

      const result = getStorageItem('test-key');

      expect(result).toEqual(testValue);
      expect(localStorageMock.getItem).toHaveBeenCalledWith('test-key');
    });

    it('should return null when item does not exist', () => {
      localStorageMock.getItem.mockReturnValue(null);

      const result = getStorageItem('test-key');

      expect(result).toBeNull();
      expect(localStorageMock.getItem).toHaveBeenCalledWith('test-key');
    });

    it('should handle empty string', () => {
      localStorageMock.getItem.mockReturnValue('');

      const result = getStorageItem('test-key');

      expect(result).toBeNull();
    });

    it('should handle primitive values', () => {
      localStorageMock.getItem.mockReturnValue('"test string"');

      const result = getStorageItem('test-key');

      expect(result).toBe('test string');
    });
  });

  describe('setStorageItem', () => {
    it('should store stringified JSON value', () => {
      const testValue = { key: 'value', number: 42 };

      setStorageItem('test-key', testValue);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'test-key',
        JSON.stringify(testValue),
      );
    });

    it('should handle primitive values', () => {
      setStorageItem('test-key', 'test string');

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'test-key',
        '"test string"',
      );
    });

    it('should handle null values', () => {
      setStorageItem('test-key', null);

      expect(localStorageMock.setItem).toHaveBeenCalledWith('test-key', 'null');
    });

    it('should handle number values', () => {
      setStorageItem('test-key', 123);

      expect(localStorageMock.setItem).toHaveBeenCalledWith('test-key', '123');
    });
  });

  describe('watchStorageItem', () => {
    it('should add event listener for storage changes', () => {
      const callback = vi.fn();

      watchStorageItem('test-key', callback);

      expect(addEventListenerMock).toHaveBeenCalledWith(
        'storage',
        expect.any(Function),
      );
    });

    it('should call callback when storage event for correct key occurs', () => {
      const callback = vi.fn();
      const testValue = { key: 'value' };

      watchStorageItem('test-key', callback);

      // Get the event handler that was registered
      const eventHandler = addEventListenerMock.mock.calls[0][1];

      // Simulate a storage event
      const storageEvent = {
        key: 'test-key',
        newValue: JSON.stringify(testValue),
      };

      eventHandler(storageEvent);

      expect(callback).toHaveBeenCalledWith(testValue);
    });

    it('should not call callback for different key', () => {
      const callback = vi.fn();

      watchStorageItem('test-key', callback);

      const eventHandler = addEventListenerMock.mock.calls[0][1];
      const storageEvent = {
        key: 'different-key',
        newValue: JSON.stringify({ key: 'value' }),
      };

      eventHandler(storageEvent);

      expect(callback).not.toHaveBeenCalled();
    });

    it('should not call callback when newValue is null', () => {
      const callback = vi.fn();

      watchStorageItem('test-key', callback);

      const eventHandler = addEventListenerMock.mock.calls[0][1];
      const storageEvent = {
        key: 'test-key',
        newValue: null,
      };

      eventHandler(storageEvent);

      expect(callback).not.toHaveBeenCalled();
    });

    it('should return cleanup function that removes event listener', () => {
      const callback = vi.fn();

      const cleanup = watchStorageItem('test-key', callback);

      expect(cleanup).toBeInstanceOf(Function);

      cleanup!();

      expect(removeEventListenerMock).toHaveBeenCalledWith(
        'storage',
        expect.any(Function),
      );
    });
  });
});
