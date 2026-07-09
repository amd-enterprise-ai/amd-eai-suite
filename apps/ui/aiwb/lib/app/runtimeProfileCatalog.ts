// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { AimImageFamily, ClusterAccelerator } from '@/types/cluster';
import {
  AUTOMATIC_IMAGE_FAMILY_ID,
  type RuntimeProfileSelectOption,
} from '@/types/runtime-profile';

export const RUNTIME_PROFILE_PRECISION_OPTIONS: RuntimeProfileSelectOption[] = [
  { key: 'bf16', label: 'bf16' },
  { key: 'fp16', label: 'fp16' },
  { key: 'fp8', label: 'fp8' },
];

export const RUNTIME_PROFILE_ACCELERATOR_TYPE_OPTIONS: RuntimeProfileSelectOption[] =
  [
    { key: 'gpu', label: 'GPU' },
    { key: 'cpu', label: 'CPU' },
  ];

export function toImageSelectOptions(
  families: AimImageFamily[],
): RuntimeProfileSelectOption[] {
  return families.map((family) => ({
    key: family.familyId,
    label: family.displayName,
  }));
}

/** Image families exposed in runtime profile forms (excludes automatic). */
export function toSelectableImageSelectOptions(
  families: AimImageFamily[],
): RuntimeProfileSelectOption[] {
  return toImageSelectOptions(families).filter(
    (option) => option.key !== AUTOMATIC_IMAGE_FAMILY_ID,
  );
}

export function toTagSelectOptions(
  families: AimImageFamily[],
  selectedFamilyId: string,
): RuntimeProfileSelectOption[] {
  if (selectedFamilyId === AUTOMATIC_IMAGE_FAMILY_ID) {
    return [];
  }
  const family = families.find((entry) => entry.familyId === selectedFamilyId);
  if (!family?.repository) {
    return [];
  }
  return family.tags.map((tag) => ({ key: tag, label: tag }));
}

export function toAcceleratorSelectOptions(
  accelerators: ClusterAccelerator[],
): RuntimeProfileSelectOption[] {
  return accelerators.map((entry) => ({
    key: entry.deviceId,
    label: entry.productName,
  }));
}

export function findImageFamily(
  families: AimImageFamily[],
  familyId: string,
): AimImageFamily | undefined {
  return families.find((family) => family.familyId === familyId);
}

/** First non-automatic image family with a repository, in catalog order. */
export function getFirstSelectableImageFamily(
  families: AimImageFamily[],
): AimImageFamily | undefined {
  return families.find(
    (family) =>
      family.familyId !== AUTOMATIC_IMAGE_FAMILY_ID && family.repository,
  );
}

function parseVersionTagParts(tag: string): number[] {
  const normalized = tag.trim().replace(/^[vV]/, '');
  if (normalized === 'latest') {
    return [Number.MAX_SAFE_INTEGER];
  }
  const parts: number[] = [];
  for (const segment of normalized.split(/[.-]/)) {
    const match = segment.match(/^\d+/);
    if (match) {
      parts.push(Number(match[0]));
    }
  }
  return parts.length > 0 ? parts : [0];
}

function compareVersionTags(a: string, b: string): number {
  const aParts = parseVersionTagParts(a);
  const bParts = parseVersionTagParts(b);
  const length = Math.max(aParts.length, bParts.length);
  for (let index = 0; index < length; index += 1) {
    const diff = (aParts[index] ?? 0) - (bParts[index] ?? 0);
    if (diff !== 0) {
      return diff;
    }
  }
  return a.localeCompare(b);
}

/** Picks the newest semver-like tag from a family catalog entry. */
export function getLatestImageTag(tags: string[]): string {
  if (tags.length === 0) {
    return '';
  }
  if (tags.length === 1) {
    return tags[0];
  }
  return [...tags].sort(compareVersionTags).at(-1) ?? tags[0];
}

export function getDefaultImageFamilySelection(families: AimImageFamily[]): {
  familyId: string;
  tag: string;
} {
  const family = getFirstSelectableImageFamily(families);
  if (!family) {
    return { familyId: '', tag: '' };
  }
  return {
    familyId: family.familyId,
    tag: getLatestImageTag(family.tags),
  };
}

/**
 * Combines repository and tag into a container image ref (`repo:tag`).
 * Preserves an embedded tag when the repository string already includes one.
 */
export function buildContainerImageRef(
  repository: string,
  tag: string,
): string {
  const image = repository.trim();
  const version = tag.trim();
  if (!image) return '';
  const tagSeparator = image.lastIndexOf(':');
  const hasEmbeddedTag = tagSeparator > -1 && tagSeparator > image.indexOf('/');
  if (hasEmbeddedTag) return image;
  return version ? `${image}:${version}` : image;
}

/**
 * Resolves the onboard image ref from catalog metadata. Automatic selection
 * omits a concrete image so the backend/aim-engine default applies; the
 * interim onboard adapter supplies a fallback ref when the API requires one.
 */
export function resolveProfileImage(
  familyId: string,
  tag: string,
  families: AimImageFamily[],
): string | undefined {
  if (familyId === AUTOMATIC_IMAGE_FAMILY_ID) {
    return undefined;
  }
  const family = findImageFamily(families, familyId);
  if (!family?.repository) {
    return undefined;
  }
  return buildContainerImageRef(family.repository, tag);
}

function imageRefFromFamily(family: AimImageFamily): string | undefined {
  if (!family.repository) {
    return undefined;
  }
  if (family.tags.length > 0) {
    return buildContainerImageRef(
      family.repository,
      getLatestImageTag(family.tags),
    );
  }
  return family.repository;
}

/** Fallback image ref when onboard requires `image` but no concrete ref was resolved. */
export function resolveDefaultOnboardImageRef(
  families: AimImageFamily[],
): string {
  const aimBase = families.find((family) => family.familyId === 'aim-base');
  const aimBaseRef = aimBase ? imageRefFromFamily(aimBase) : undefined;
  if (aimBaseRef) {
    return aimBaseRef;
  }

  const catalogFamily = families.find(
    (family) =>
      family.familyId !== AUTOMATIC_IMAGE_FAMILY_ID && family.repository,
  );
  const catalogRef = catalogFamily
    ? imageRefFromFamily(catalogFamily)
    : undefined;
  if (catalogRef) {
    return catalogRef;
  }

  return 'amdenterpriseai/aim-base';
}

export function getDefaultAcceleratorDeviceId(
  accelerators: ClusterAccelerator[],
): string {
  return accelerators[0]?.deviceId ?? '';
}

/**
 * Base-template supported counts capped by the cluster's allocatable device
 * count (unsupported sizes leave the profile `NotAvailable`). Falls back to the
 * full supported set if the cap empties it, so incomplete capacity data never
 * blocks onboarding. Returns `[]` when no supported counts are known.
 */
export function supportedAcceleratorCounts(
  baseCounts: number[],
  allocatableCount: number,
): number[] {
  const supported = Array.from(new Set(baseCounts))
    .filter((count) => Number.isInteger(count) && count > 0)
    .sort((a, b) => a - b);
  if (supported.length === 0) {
    return [];
  }
  const capped =
    allocatableCount > 0
      ? supported.filter((count) => count <= allocatableCount)
      : supported;
  return capped.length > 0 ? capped : supported;
}

/** Vendor prefixes stripped from a node `productName`. Most-specific first so `AMD Instinct ` wins over `AMD `. */
const ACCELERATOR_PRODUCT_PREFIXES = ['AMD Instinct ', 'AMD Radeon ', 'AMD '];

/** Form-factor tokens the GPU operator appends to product names but aim-engine drops (e.g. `MI300X OAM` -> `MI300X`). */
const ACCELERATOR_FORM_FACTOR_SUFFIXES = ['OAM', 'APU', 'GPU'];

/**
 * Reduce a node `productName` (e.g. `AMD Instinct MI300X OAM`) to the bare token
 * aim-engine keys `acceleratorModel` on (`MI300X`): match the Instinct token
 * directly, else strip the vendor prefix and form-factor suffixes. Sending the
 * un-normalized name leaves a custom profile stuck `NotAvailable`.
 */
export function canonicalAcceleratorModel(productName: string): string {
  const normalized = productName.trim().replace(/_/g, ' ').replace(/\s+/g, ' ');
  const instinctModel = normalized.match(/\bMI\d{2,}[A-Za-z]*\b/i);
  if (instinctModel) {
    return instinctModel[0].toUpperCase();
  }
  let name = normalized;
  for (const prefix of ACCELERATOR_PRODUCT_PREFIXES) {
    if (name.startsWith(prefix)) {
      name = name.slice(prefix.length).trim();
      break;
    }
  }
  const tokens = name.split(' ').filter(Boolean);
  while (
    tokens.length > 1 &&
    ACCELERATOR_FORM_FACTOR_SUFFIXES.includes(
      tokens[tokens.length - 1].toUpperCase(),
    )
  ) {
    tokens.pop();
  }
  return tokens.join(' ');
}

/**
 * Resolve a selected device id (`74a1`) to the canonical `acceleratorModel`
 * (`MI300X`) before persisting; the raw device id leaves the profile
 * `NotAvailable`. Falls back to the input when the device id is unknown.
 */
export function deviceIdToAcceleratorModel(
  deviceId: string,
  accelerators: ClusterAccelerator[],
): string {
  const id = deviceId.trim();
  if (!id) {
    return id;
  }
  const match = accelerators.find((entry) => entry.deviceId === id);
  if (!match) {
    return id;
  }
  return canonicalAcceleratorModel(match.productName) || id;
}

/**
 * Inverse of {@link deviceIdToAcceleratorModel} for edit prefill: map a persisted
 * `acceleratorModel` back to the dropdown's device id. Tolerates legacy device
 * ids and unknown values (returned as-is).
 */
export function acceleratorModelToDeviceId(
  model: string | undefined,
  accelerators: ClusterAccelerator[],
): string {
  const value = model?.trim();
  if (!value) {
    return '';
  }
  const byDeviceId = accelerators.find((entry) => entry.deviceId === value);
  if (byDeviceId) {
    return byDeviceId.deviceId;
  }
  const byModel = accelerators.find(
    (entry) => canonicalAcceleratorModel(entry.productName) === value,
  );
  if (byModel) {
    return byModel.deviceId;
  }
  return value;
}
