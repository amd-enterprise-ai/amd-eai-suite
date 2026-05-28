// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect, vi, beforeEach } from 'vitest';

import {
  fileToBase64DataUrl,
  isValidImageFile,
  formatFileSize,
  extractTextContent,
  MAX_IMAGE_FILE_SIZE,
} from '@/lib/app/image-utils';

describe('image-utils', () => {
  describe('isValidImageFile', () => {
    const makeFile = (type: string, size = 1024) =>
      new File(['x'.repeat(size)], 'test', { type });

    it('accepts jpeg', () => {
      expect(isValidImageFile(makeFile('image/jpeg'))).toBe(true);
    });

    it('accepts png', () => {
      expect(isValidImageFile(makeFile('image/png'))).toBe(true);
    });

    it('accepts gif', () => {
      expect(isValidImageFile(makeFile('image/gif'))).toBe(true);
    });

    it('accepts webp', () => {
      expect(isValidImageFile(makeFile('image/webp'))).toBe(true);
    });

    it('rejects pdf', () => {
      expect(isValidImageFile(makeFile('application/pdf'))).toBe(false);
    });

    it('rejects plain text', () => {
      expect(isValidImageFile(makeFile('text/plain'))).toBe(false);
    });

    it('rejects zero-byte files', () => {
      expect(isValidImageFile(makeFile('image/png', 0))).toBe(false);
    });

    it('accepts a file exactly at the size limit', () => {
      const file = Object.defineProperty(makeFile('image/png'), 'size', {
        value: MAX_IMAGE_FILE_SIZE,
      });
      expect(isValidImageFile(file)).toBe(true);
    });

    it('rejects a file one byte over the size limit', () => {
      const file = Object.defineProperty(makeFile('image/png'), 'size', {
        value: MAX_IMAGE_FILE_SIZE + 1,
      });
      expect(isValidImageFile(file)).toBe(false);
    });
  });

  describe('formatFileSize', () => {
    it('returns "0 Bytes" for zero', () => {
      expect(formatFileSize(0)).toBe('0 Bytes');
    });

    it('formats bytes', () => {
      expect(formatFileSize(500)).toBe('500 Bytes');
    });

    it('formats kilobytes', () => {
      expect(formatFileSize(1024)).toBe('1 KB');
    });

    it('formats megabytes', () => {
      expect(formatFileSize(1024 * 1024)).toBe('1 MB');
    });

    it('rounds to two decimal places', () => {
      expect(formatFileSize(1536)).toBe('1.5 KB');
    });
  });

  describe('extractTextContent', () => {
    it('returns string content unchanged', () => {
      expect(extractTextContent('hello')).toBe('hello');
    });

    it('returns empty string for empty string input', () => {
      expect(extractTextContent('')).toBe('');
    });

    it('extracts text from a single text item', () => {
      expect(extractTextContent([{ type: 'text', text: 'hello' }])).toBe(
        'hello',
      );
    });

    it('joins multiple text items with newline', () => {
      expect(
        extractTextContent([
          { type: 'text', text: 'line 1' },
          { type: 'text', text: 'line 2' },
        ]),
      ).toBe('line 1\nline 2');
    });

    it('ignores image_url items', () => {
      expect(
        extractTextContent([
          { type: 'text', text: 'caption' },
          {
            type: 'image_url',
            image_url: { url: 'data:image/png;base64,abc' },
          },
        ]),
      ).toBe('caption');
    });

    it('returns empty string when only image_url items are present', () => {
      expect(
        extractTextContent([
          {
            type: 'image_url',
            image_url: { url: 'data:image/png;base64,abc' },
          },
        ]),
      ).toBe('');
    });

    it('returns empty string for empty array', () => {
      expect(extractTextContent([])).toBe('');
    });
  });

  describe('fileToBase64DataUrl', () => {
    beforeEach(() => {
      vi.restoreAllMocks();
    });

    it('resolves with the data URL on success', async () => {
      const fakeDataUrl = 'data:image/png;base64,abc123';

      class MockFileReader {
        onload: ((e: any) => void) | null = null;
        onerror: ((e: any) => void) | null = null;
        result = fakeDataUrl;

        readAsDataURL() {
          Promise.resolve().then(() => this.onload?.({}));
        }
      }

      vi.stubGlobal('FileReader', MockFileReader);

      const file = new File(['img'], 'test.png', { type: 'image/png' });
      await expect(fileToBase64DataUrl(file)).resolves.toBe(fakeDataUrl);
    });

    it('rejects when the FileReader errors', async () => {
      const fakeError = new DOMException('read error');

      class MockFileReader {
        onload: ((e: any) => void) | null = null;
        onerror: ((e: any) => void) | null = null;
        result = null;
        error = fakeError;

        readAsDataURL() {
          Promise.resolve().then(() => this.onerror?.({}));
        }
      }

      vi.stubGlobal('FileReader', MockFileReader);

      const file = new File(['img'], 'test.png', { type: 'image/png' });
      await expect(fileToBase64DataUrl(file)).rejects.toBe(fakeError);
    });
  });
});
