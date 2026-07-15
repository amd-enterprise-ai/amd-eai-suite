// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, expect, it } from 'vitest';

import {
  acceleratorModelToDeviceId,
  buildContainerImageRef,
  canonicalAcceleratorModel,
  deviceIdToAcceleratorModel,
  getDefaultAcceleratorDeviceId,
  getDefaultImageFamilySelection,
  getFirstSelectableImageFamily,
  getLatestImageTag,
  resolveDefaultOnboardImageRef,
  resolveProfileImage,
  supportedAcceleratorCounts,
  toAcceleratorSelectOptions,
  toImageSelectOptions,
  toSelectableImageSelectOptions,
  toTagSelectOptions,
} from '@/lib/app/runtimeProfileCatalog';
import type { AimImageFamily, ClusterAccelerator } from '@/types/cluster';
import { AUTOMATIC_IMAGE_FAMILY_ID } from '@/types/runtime-profile';

const imageFamilies: AimImageFamily[] = [
  {
    familyId: 'automatic',
    displayName: 'Automatic',
    repository: null,
    tags: [],
  },
  {
    familyId: 'aim-base',
    displayName: 'aim-base',
    repository: 'amdenterpriseai/aim-base',
    tags: ['0.11'],
  },
];

const accelerators: ClusterAccelerator[] = [
  {
    deviceId: '74a1',
    productName: 'AMD Instinct MI300X',
    allocatableCount: 8,
  },
];

describe('runtimeProfileCatalog transforms', () => {
  it('maps image families to select options', () => {
    expect(toImageSelectOptions(imageFamilies)).toEqual([
      { key: 'automatic', label: 'Automatic' },
      { key: 'aim-base', label: 'aim-base' },
    ]);
  });

  it('excludes automatic from selectable image options', () => {
    expect(toSelectableImageSelectOptions(imageFamilies)).toEqual([
      { key: 'aim-base', label: 'aim-base' },
    ]);
  });

  it('returns no tags for automatic family', () => {
    expect(
      toTagSelectOptions(imageFamilies, AUTOMATIC_IMAGE_FAMILY_ID),
    ).toEqual([]);
  });

  it('maps aim-base tags to select options', () => {
    expect(toTagSelectOptions(imageFamilies, 'aim-base')).toEqual([
      { key: '0.11', label: '0.11' },
    ]);
  });

  it('maps accelerators to select options', () => {
    expect(toAcceleratorSelectOptions(accelerators)).toEqual([
      { key: '74a1', label: 'AMD Instinct MI300X' },
    ]);
  });

  it('buildContainerImageRef combines repository and tag', () => {
    expect(buildContainerImageRef('amdenterpriseai/aim-base', '0.11')).toBe(
      'amdenterpriseai/aim-base:0.11',
    );
  });

  it('resolveProfileImage omits image for automatic selection', () => {
    expect(resolveProfileImage('automatic', '', imageFamilies)).toBeUndefined();
  });

  it('resolveProfileImage builds concrete image ref', () => {
    expect(resolveProfileImage('aim-base', '0.11', imageFamilies)).toBe(
      'amdenterpriseai/aim-base:0.11',
    );
  });

  it('resolveDefaultOnboardImageRef uses first selectable catalog family', () => {
    expect(resolveDefaultOnboardImageRef(imageFamilies)).toBe(
      'amdenterpriseai/aim-base:0.11',
    );
  });

  it('resolveDefaultOnboardImageRef preselects a radeon-only family and latest discovered tag', () => {
    expect(
      resolveDefaultOnboardImageRef([
        {
          familyId: 'automatic',
          displayName: 'Automatic',
          repository: null,
          tags: [],
        },
        {
          familyId: 'radeon-aim-base',
          displayName: 'radeon-aim-base',
          repository: 'docker.io/silogenai/radeon-aim-base',
          tags: ['0.11-preview', '0.12-preview'],
        },
      ]),
    ).toBe('docker.io/silogenai/radeon-aim-base:0.12-preview');
  });

  it('resolveDefaultOnboardImageRef falls back to unpinned aim-base when catalog is empty', () => {
    expect(resolveDefaultOnboardImageRef([])).toBe('amdenterpriseai/aim-base');
  });

  it('getLatestImageTag picks the newest semver-like tag', () => {
    expect(getLatestImageTag(['0.9', '0.11', '0.10'])).toBe('0.11');
    expect(getLatestImageTag(['latest', '0.11'])).toBe('latest');
  });

  it('getFirstSelectableImageFamily skips automatic', () => {
    expect(getFirstSelectableImageFamily(imageFamilies)?.familyId).toBe(
      'aim-base',
    );
  });

  it('getDefaultImageFamilySelection returns first family and latest tag', () => {
    expect(getDefaultImageFamilySelection(imageFamilies)).toEqual({
      familyId: 'aim-base',
      tag: '0.11',
    });
  });

  it('getDefaultAcceleratorDeviceId returns the first catalog device id', () => {
    expect(getDefaultAcceleratorDeviceId(accelerators)).toBe('74a1');
    expect(getDefaultAcceleratorDeviceId([])).toBe('');
  });
});

describe('accelerator model resolution', () => {
  it('canonicalAcceleratorModel extracts the MIxxx token, dropping form-factor suffixes', () => {
    expect(canonicalAcceleratorModel('AMD Instinct MI300X')).toBe('MI300X');
    // The GPU operator reports this exact name; aim-engine wants MI300X.
    expect(canonicalAcceleratorModel('AMD Instinct MI300X OAM')).toBe('MI300X');
    expect(canonicalAcceleratorModel('AMD_Instinct_MI300X_OAM')).toBe('MI300X');
    expect(canonicalAcceleratorModel('AMD Instinct MI325X')).toBe('MI325X');
    expect(canonicalAcceleratorModel('MI300X')).toBe('MI300X');
  });

  it('canonicalAcceleratorModel extracts the Radeon [RW]#### token, dropping the marketing suffix', () => {
    // The GPU operator reports R9700S; aim-engine keys on R9700.
    expect(canonicalAcceleratorModel('AMD Radeon AI PRO R9700S')).toBe('R9700');
    expect(canonicalAcceleratorModel('AMD_Radeon_AI_PRO_R9700S')).toBe('R9700');
    expect(canonicalAcceleratorModel('AMD Radeon PRO W7900')).toBe('W7900');
    expect(canonicalAcceleratorModel('W7900')).toBe('W7900');
  });

  it('canonicalAcceleratorModel falls back to prefix/suffix stripping for unrecognized parts', () => {
    expect(canonicalAcceleratorModel('AMD Radeon RX 7900 XTX')).toBe(
      'RX 7900 XTX',
    );
  });

  it('deviceIdToAcceleratorModel maps a device id to the canonical model', () => {
    expect(deviceIdToAcceleratorModel('74a1', accelerators)).toBe('MI300X');
    expect(
      deviceIdToAcceleratorModel('74a1', [
        {
          deviceId: '74a1',
          productName: 'AMD Instinct MI300X OAM',
          allocatableCount: 8,
        },
      ]),
    ).toBe('MI300X');
  });

  it('deviceIdToAcceleratorModel passes unknown/blank values through', () => {
    expect(deviceIdToAcceleratorModel('MI325X', accelerators)).toBe('MI325X');
    expect(deviceIdToAcceleratorModel('', accelerators)).toBe('');
  });

  it('acceleratorModelToDeviceId resolves a canonical model back to its device id', () => {
    expect(acceleratorModelToDeviceId('MI300X', accelerators)).toBe('74a1');
    // Edit prefill: persisted MI300X resolves back even when the catalog
    // reports the form-factor-suffixed product name.
    expect(
      acceleratorModelToDeviceId('MI300X', [
        {
          deviceId: '74a1',
          productName: 'AMD Instinct MI300X OAM',
          allocatableCount: 8,
        },
      ]),
    ).toBe('74a1');
  });

  it('acceleratorModelToDeviceId tolerates legacy device ids and unknown values', () => {
    expect(acceleratorModelToDeviceId('74a1', accelerators)).toBe('74a1');
    expect(acceleratorModelToDeviceId('MI325X', accelerators)).toBe('MI325X');
    expect(acceleratorModelToDeviceId(undefined, accelerators)).toBe('');
  });

  it('supportedAcceleratorCounts caps the base sizes by allocatable capacity', () => {
    expect(supportedAcceleratorCounts([1, 2, 4, 8], 4)).toEqual([1, 2, 4]);
    expect(supportedAcceleratorCounts([8, 1, 4, 2], 8)).toEqual([1, 2, 4, 8]);
  });

  it('supportedAcceleratorCounts deduplicates sizes', () => {
    expect(supportedAcceleratorCounts([2, 1, 2, 1, 4], 8)).toEqual([1, 2, 4]);
  });

  it('supportedAcceleratorCounts ignores the cap when capacity is unknown', () => {
    expect(supportedAcceleratorCounts([1, 2, 4, 8], 0)).toEqual([1, 2, 4, 8]);
  });

  it('supportedAcceleratorCounts keeps the full set when the cap would empty it', () => {
    // Incomplete capacity data must not block onboarding entirely.
    expect(supportedAcceleratorCounts([2, 4, 8], 1)).toEqual([2, 4, 8]);
  });

  it('supportedAcceleratorCounts drops non-positive/non-integer sizes and returns [] when none remain', () => {
    expect(supportedAcceleratorCounts([0, -2, 1.5], 8)).toEqual([]);
    expect(supportedAcceleratorCounts([], 8)).toEqual([]);
  });
});
