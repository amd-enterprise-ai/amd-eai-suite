// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect, vi } from 'vitest';
import {
  getWorkloadTypeFilterItems,
  getWorkloadStatusFilterItems,
  WORKLOAD_STATUS_COLOR_MAP,
} from '@amdenterpriseai/utils/app';
import { WorkloadType, WorkloadStatus } from '@amdenterpriseai/types';

describe('getWorkloadTypeFilterItems', () => {
  it('should return all workload types', () => {
    const mockT = (key: string) => `translated-${key}`;
    const result = getWorkloadTypeFilterItems(mockT);

    expect(result).toHaveLength(5);
    expect(result.map((item) => item.key)).toEqual([
      WorkloadType.MODEL_DOWNLOAD,
      WorkloadType.INFERENCE,
      WorkloadType.FINE_TUNING,
      WorkloadType.WORKSPACE,
      WorkloadType.CUSTOM,
    ]);
  });

  it('should call translation function with correct keys', () => {
    const mockT = vi.fn((key: string) => `translated-${key}`);
    const result = getWorkloadTypeFilterItems(mockT);

    expect(mockT).toHaveBeenCalledWith(`type.${WorkloadType.MODEL_DOWNLOAD}`);
    expect(mockT).toHaveBeenCalledWith(`type.${WorkloadType.INFERENCE}`);
    expect(mockT).toHaveBeenCalledWith(`type.${WorkloadType.FINE_TUNING}`);
    expect(mockT).toHaveBeenCalledWith(`type.${WorkloadType.WORKSPACE}`);
    expect(mockT).toHaveBeenCalledWith(`type.${WorkloadType.CUSTOM}`);
  });

  it('should set labels from translation function', () => {
    const mockT = (key: string) => `translated-${key}`;
    const result = getWorkloadTypeFilterItems(mockT);

    result.forEach((item) => {
      expect(item.label).toContain('translated-');
    });
  });
});

describe('getWorkloadStatusFilterItems', () => {
  it('should return all workload statuses', () => {
    const mockT = (key: string) => `translated-${key}`;
    const result = getWorkloadStatusFilterItems(mockT);

    expect(result).toHaveLength(10);
    expect(result.map((item) => item.key)).toEqual([
      WorkloadStatus.ADDED,
      WorkloadStatus.PENDING,
      WorkloadStatus.RUNNING,
      WorkloadStatus.TERMINATED,
      WorkloadStatus.COMPLETE,
      WorkloadStatus.FAILED,
      WorkloadStatus.UNKNOWN,
      WorkloadStatus.DELETING,
      WorkloadStatus.DELETE_FAILED,
      WorkloadStatus.DELETED,
    ]);
  });

  it('should call translation function with correct keys', () => {
    const mockT = vi.fn((key: string) => `translated-${key}`);
    getWorkloadStatusFilterItems(mockT);

    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.ADDED}`);
    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.PENDING}`);
    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.RUNNING}`);
    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.TERMINATED}`);
    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.COMPLETE}`);
    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.FAILED}`);
    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.UNKNOWN}`);
    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.DELETING}`);
    expect(mockT).toHaveBeenCalledWith(
      `status.${WorkloadStatus.DELETE_FAILED}`,
    );
    expect(mockT).toHaveBeenCalledWith(`status.${WorkloadStatus.DELETED}`);
  });

  it('should set labels from translation function', () => {
    const mockT = (key: string) => `translated-${key}`;
    const result = getWorkloadStatusFilterItems(mockT);

    result.forEach((item) => {
      expect(item.label).toContain('translated-');
    });
  });

  it('should have showDivider only on DELETE_FAILED', () => {
    const mockT = (key: string) => `translated-${key}`;
    const result = getWorkloadStatusFilterItems(mockT);

    const itemsWithDivider = result.filter((item) => item.showDivider);
    expect(itemsWithDivider).toHaveLength(1);
    expect(itemsWithDivider[0].key).toBe(WorkloadStatus.DELETE_FAILED);
  });
});

describe('WORKLOAD_STATUS_COLOR_MAP', () => {
  it('should have color mappings for all workload statuses', () => {
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.FAILED]).toBe('red');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.PENDING]).toBe('gray');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.RUNNING]).toBe('blue');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.COMPLETE]).toBe('green');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.DELETE_FAILED]).toBe(
      'amber',
    );
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.TERMINATED]).toBe('gray');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.UNKNOWN]).toBe('darkgray');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.DELETED]).toBe('emerald');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.ADDED]).toBe('cyan');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.DELETING]).toBe('fuchsia');
    expect(WORKLOAD_STATUS_COLOR_MAP[WorkloadStatus.DOWNLOADING]).toBe(
      'violet',
    );
  });

  it('should have entries for all WorkloadStatus enum values', () => {
    const statusKeys = Object.keys(WorkloadStatus);
    const mapKeys = Object.keys(WORKLOAD_STATUS_COLOR_MAP);

    expect(mapKeys.length).toBe(statusKeys.length);
  });
});
