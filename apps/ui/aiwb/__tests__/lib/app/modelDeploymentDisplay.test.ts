// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, expect, it } from 'vitest';

import {
  formatTemplateGpuCount,
  formatModelDeploymentSubtitle,
} from '@/lib/app/modelDeploymentDisplay';

describe('formatTemplateGpuCount', () => {
  it('returns "Nx GPU" when acceleratorType is not provided', () => {
    expect(formatTemplateGpuCount(8)).toBe('8x GPU');
  });

  it('returns "Nx GPU" when acceleratorType is gpu', () => {
    expect(formatTemplateGpuCount(4, 'gpu')).toBe('4x GPU');
  });

  it('returns "Nx GPU" when acceleratorType is null', () => {
    expect(formatTemplateGpuCount(2, null)).toBe('2x GPU');
  });

  it('returns "Nx GPU" when acceleratorType is undefined', () => {
    expect(formatTemplateGpuCount(2, undefined)).toBe('2x GPU');
  });

  it('returns "Nx CPU" when acceleratorType is cpu', () => {
    expect(formatTemplateGpuCount(1, 'cpu')).toBe('1x CPU');
  });

  it('is case-insensitive for acceleratorType', () => {
    expect(formatTemplateGpuCount(1, 'CPU')).toBe('1x CPU');
  });

  it('trims whitespace from acceleratorType before comparison', () => {
    expect(formatTemplateGpuCount(1, ' cpu ')).toBe('1x CPU');
  });
});

describe('formatModelDeploymentSubtitle', () => {
  const t = (key: string) => key;

  it('returns empty string when no parts are present', () => {
    expect(formatModelDeploymentSubtitle(t as any, {})).toBe('');
  });

  it('formats GPU count using acceleratorType', () => {
    const result = formatModelDeploymentSubtitle(t as any, {
      templateGpuCount: 1,
      acceleratorType: 'cpu',
    });
    expect(result).toBe('1x CPU');
  });

  it('formats GPU count as GPU when acceleratorType is gpu', () => {
    const result = formatModelDeploymentSubtitle(t as any, {
      templateGpuCount: 8,
      acceleratorType: 'gpu',
    });
    expect(result).toBe('8x GPU');
  });

  it('formats GPU count as GPU when acceleratorType is absent', () => {
    const result = formatModelDeploymentSubtitle(t as any, {
      templateGpuCount: 4,
    });
    expect(result).toBe('4x GPU');
  });

  it('joins all parts with · separator', () => {
    const result = formatModelDeploymentSubtitle(t as any, {
      imageVersion: '1.0',
      templateGpuCount: 8,
      acceleratorType: 'gpu',
      precision: 'fp16',
    });
    expect(result).toBe('1.0 · 8x GPU · fp16');
  });
});
