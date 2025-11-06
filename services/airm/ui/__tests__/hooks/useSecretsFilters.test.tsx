// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';

import { useSecretsFilters } from '@/hooks/useSecretsFilters';
import { SecretType, SecretScope } from '@/types/enums/secrets';

describe('useSecretsFilters', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with empty filters', () => {
    const { result } = renderHook(() => useSecretsFilters());

    expect(result.current.filters).toEqual([]);
  });

  it('includes scope in filter config by default', () => {
    const { result } = renderHook(() => useSecretsFilters());

    expect(result.current.filterConfig).toHaveProperty('scope');
  });

  it('excludes scope from filter config when includeScope is false', () => {
    const { result } = renderHook(() =>
      useSecretsFilters({ includeScope: false }),
    );

    expect(result.current.filterConfig).not.toHaveProperty('scope');
  });

  it('always includes search and type in filter config', () => {
    const { result } = renderHook(() => useSecretsFilters());

    expect(result.current.filterConfig).toHaveProperty('search');
    expect(result.current.filterConfig).toHaveProperty('type');
  });

  it('handles filter change for search', () => {
    const { result } = renderHook(() => useSecretsFilters());

    act(() => {
      result.current.handleFilterChange({ search: ['test'] });
    });

    expect(result.current.filters).toHaveLength(1);
    expect(result.current.filters[0]).toEqual({
      field: 'name',
      values: ['test'],
    });
  });

  it('handles filter change for type', () => {
    const { result } = renderHook(() => useSecretsFilters());

    act(() => {
      result.current.handleFilterChange({ type: [SecretType.EXTERNAL] });
    });

    expect(result.current.filters).toHaveLength(1);
    expect(result.current.filters[0]).toEqual({
      field: 'type',
      values: [SecretType.EXTERNAL],
    });
  });

  it('handles filter change for scope when includeScope is true', () => {
    const { result } = renderHook(() => useSecretsFilters());

    act(() => {
      result.current.handleFilterChange({
        scope: [SecretScope.ORGANIZATION],
      });
    });

    expect(result.current.filters).toHaveLength(1);
    expect(result.current.filters[0]).toEqual({
      field: 'scope',
      values: [SecretScope.ORGANIZATION],
    });
  });

  it('ignores scope filter when includeScope is false', () => {
    const { result } = renderHook(() =>
      useSecretsFilters({ includeScope: false }),
    );

    act(() => {
      result.current.handleFilterChange({
        scope: [SecretScope.ORGANIZATION],
      });
    });

    expect(result.current.filters).toHaveLength(0);
  });

  it('handles multiple filters simultaneously', () => {
    const { result } = renderHook(() => useSecretsFilters());

    act(() => {
      result.current.handleFilterChange({
        search: ['test'],
        type: [SecretType.EXTERNAL],
        scope: [SecretScope.ORGANIZATION],
      });
    });

    expect(result.current.filters).toHaveLength(3);
  });

  it('ignores empty search arrays', () => {
    const { result } = renderHook(() => useSecretsFilters());

    act(() => {
      result.current.handleFilterChange({ search: [] });
    });

    expect(result.current.filters).toHaveLength(0);
  });

  it('ignores search array with single empty string', () => {
    const { result } = renderHook(() => useSecretsFilters());

    act(() => {
      result.current.handleFilterChange({ search: [''] });
    });

    expect(result.current.filters).toHaveLength(0);
  });

  it('clears previous filters when new filter is applied', () => {
    const { result } = renderHook(() => useSecretsFilters());

    act(() => {
      result.current.handleFilterChange({ search: ['test'] });
    });

    expect(result.current.filters).toHaveLength(1);

    act(() => {
      result.current.handleFilterChange({ type: [SecretType.EXTERNAL] });
    });

    expect(result.current.filters).toHaveLength(1);
    expect(result.current.filters[0].field).toBe('type');
  });
});
