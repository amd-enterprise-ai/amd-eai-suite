// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@amdenterpriseai/utils/app';
import { describe, it, expect } from 'vitest';

describe('getErrorMessage', () => {
  it('should extract error message from response body error field (string)', async () => {
    const response = new Response(
      JSON.stringify({ error: 'Error message from API' }),
      { status: 400 },
    );
    const result = await getErrorMessage(response);
    expect(result).toBe('Error message from API');
  });

  it('should extract error message from response body message field', async () => {
    const response = new Response(
      JSON.stringify({ message: 'Message field takes priority' }),
      { status: 400 },
    );
    const result = await getErrorMessage(response);
    expect(result).toBe('Message field takes priority');
  });

  it('should extract error message from APIErrorContent object', async () => {
    const response = new Response(
      JSON.stringify({ error: { message: 'Error from APIErrorContent' } }),
      { status: 400 },
    );
    const result = await getErrorMessage(response);
    expect(result).toBe('Error from APIErrorContent');
  });

  it('should fallback to statusText when error and message are not present', async () => {
    const response = new Response(JSON.stringify({}), {
      status: 500,
      statusText: 'Internal Server Error',
    });
    const result = await getErrorMessage(response);
    expect(result).toBe('Internal Server Error');
  });

  it('should handle non-JSON response gracefully', async () => {
    const response = new Response('Not JSON', {
      status: 500,
      statusText: 'Server Error',
    });
    const result = await getErrorMessage(response);
    // When JSON parsing fails, it returns the parse error message
    expect(result).toContain('Not JSON');
  });

  it('should handle empty statusText by returning parse error message', async () => {
    const response = new Response('Not JSON', {
      status: 500,
      statusText: '',
    });
    const result = await getErrorMessage(response);
    // When JSON parsing fails, it returns the parse error message
    expect(result).toContain('Not JSON');
  });

  it('should prioritize error field over message field', async () => {
    const response = new Response(
      JSON.stringify({
        error: 'Error field takes priority',
        message: 'This should be ignored',
      }),
      { status: 400 },
    );
    const result = await getErrorMessage(response);
    expect(result).toBe('Error field takes priority');
  });
});
