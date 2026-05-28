// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  createMailtoLink,
  isHttpUrl,
  stripTrailingSlashes,
} from '@amdenterpriseai/utils/app';

import { describe, expect, it } from 'vitest';

describe('isHttpUrl', () => {
  describe('valid HTTP/HTTPS URLs', () => {
    it('should return true for http URL', () => {
      expect(isHttpUrl('http://example.com')).toBe(true);
    });

    it('should return true for https URL', () => {
      expect(isHttpUrl('https://example.com')).toBe(true);
    });

    it('should return true for URL with path', () => {
      expect(isHttpUrl('https://example.com/path/to/resource')).toBe(true);
    });

    it('should return true for URL with query string', () => {
      expect(isHttpUrl('https://example.com/path?foo=bar&baz=qux')).toBe(true);
    });

    it('should return true for URL with port', () => {
      expect(isHttpUrl('http://localhost:3000')).toBe(true);
    });

    it('should return true for URL with fragment', () => {
      expect(isHttpUrl('https://example.com/page#section')).toBe(true);
    });
  });

  describe('uppercase schemes', () => {
    it('should return true for uppercase HTTP', () => {
      expect(isHttpUrl('HTTP://example.com')).toBe(true);
    });

    it('should return true for uppercase HTTPS', () => {
      expect(isHttpUrl('HTTPS://example.com')).toBe(true);
    });

    it('should return true for mixed case scheme', () => {
      expect(isHttpUrl('HtTpS://example.com')).toBe(true);
    });
  });

  describe('invalid URLs without host', () => {
    it('should return false for http:// without host', () => {
      expect(isHttpUrl('http://')).toBe(false);
    });

    it('should return false for https:// without host', () => {
      expect(isHttpUrl('https://')).toBe(false);
    });

    it('should return false for http:// with only spaces', () => {
      expect(isHttpUrl('http://   ')).toBe(false);
    });
  });

  describe('empty and whitespace', () => {
    it('should return false for empty string', () => {
      expect(isHttpUrl('')).toBe(false);
    });

    it('should return false for whitespace-only string', () => {
      expect(isHttpUrl('   ')).toBe(false);
    });

    it('should handle URL with leading/trailing whitespace', () => {
      expect(isHttpUrl('  https://example.com  ')).toBe(true);
    });
  });

  describe('non-HTTP schemes', () => {
    it('should return false for ftp URL', () => {
      expect(isHttpUrl('ftp://example.com')).toBe(false);
    });

    it('should return false for javascript URL', () => {
      expect(isHttpUrl('javascript:alert(1)')).toBe(false);
    });

    it('should return false for data URL', () => {
      expect(isHttpUrl('data:text/html,<h1>Hello</h1>')).toBe(false);
    });

    it('should return false for file URL', () => {
      expect(isHttpUrl('file:///etc/passwd')).toBe(false);
    });

    it('should return false for mailto URL', () => {
      expect(isHttpUrl('mailto:user@example.com')).toBe(false);
    });
  });

  describe('malformed URLs', () => {
    it('should return false for plain text', () => {
      expect(isHttpUrl('not a url')).toBe(false);
    });

    it('should return false for URL without scheme', () => {
      expect(isHttpUrl('example.com')).toBe(false);
    });

    it('should return false for URL with invalid characters', () => {
      expect(isHttpUrl('http://exam ple.com')).toBe(false);
    });
  });
});

describe('stripTrailingSlashes', () => {
  it('should remove a single trailing slash', () => {
    expect(stripTrailingSlashes('https://example.com/')).toBe(
      'https://example.com',
    );
  });

  it('should remove multiple trailing slashes', () => {
    expect(stripTrailingSlashes('https://example.com///')).toBe(
      'https://example.com',
    );
  });

  it('should not modify URL without trailing slash', () => {
    expect(stripTrailingSlashes('https://example.com')).toBe(
      'https://example.com',
    );
  });

  it('should preserve path segments', () => {
    expect(stripTrailingSlashes('https://example.com/path/to/resource/')).toBe(
      'https://example.com/path/to/resource',
    );
  });

  it('should handle empty string', () => {
    expect(stripTrailingSlashes('')).toBe('');
  });

  it('should handle string with only slashes', () => {
    expect(stripTrailingSlashes('///')).toBe('');
  });
});

describe('createMailtoLink', () => {
  const expectedPrefix = 'mailto:amd-eai-support@amd.com';

  it('should return a bare mailto link when called with no args', () => {
    expect(createMailtoLink()).toBe(expectedPrefix);
  });

  it('should return a bare mailto link when called with empty args', () => {
    expect(createMailtoLink({})).toBe(expectedPrefix);
  });

  it('should encode the subject', () => {
    expect(createMailtoLink({ subject: 'Hello world' })).toBe(
      `${expectedPrefix}?subject=Hello%20world`,
    );
  });

  it('should encode a string body', () => {
    expect(createMailtoLink({ body: 'Line one' })).toBe(
      `${expectedPrefix}?body=Line%20one`,
    );
  });

  it('should join an array body with line breaks', () => {
    const result = createMailtoLink({ body: ['Line one', 'Line two'] });
    expect(result).toBe(`${expectedPrefix}?body=Line%20one%0ALine%20two`);
  });

  it('should include both subject and body when provided', () => {
    const result = createMailtoLink({
      subject: 'Request',
      body: ['Hello', 'World'],
    });
    expect(result).toBe(`${expectedPrefix}?subject=Request&body=Hello%0AWorld`);
  });

  it('should encode special characters in subject and body', () => {
    const result = createMailtoLink({
      subject: 'A & B',
      body: 'name=value?x',
    });
    expect(result).toBe(
      `${expectedPrefix}?subject=A%20%26%20B&body=name%3Dvalue%3Fx`,
    );
  });

  it('should preserve empty lines inside an array body', () => {
    const result = createMailtoLink({ body: ['First', '', 'Third'] });
    expect(result).toBe(`${expectedPrefix}?body=First%0A%0AThird`);
  });

  it('should omit empty subject', () => {
    expect(createMailtoLink({ subject: '', body: 'hi' })).toBe(
      `${expectedPrefix}?body=hi`,
    );
  });

  it('should omit empty body', () => {
    expect(createMailtoLink({ subject: 'hi', body: '' })).toBe(
      `${expectedPrefix}?subject=hi`,
    );
  });

  it('should omit empty array body', () => {
    expect(createMailtoLink({ subject: 'hi', body: [] })).toBe(
      `${expectedPrefix}?subject=hi`,
    );
  });
});
