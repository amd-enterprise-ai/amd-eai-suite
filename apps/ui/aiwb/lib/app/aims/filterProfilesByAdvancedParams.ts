// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { AIMClusterServiceTemplate } from '@/types/aims';

/** Form sentinel: control does not narrow templates for that dimension (automatic selection). */
export const ADVANCED_PARAM_AUTOMATIC = '__automatic__';

export type FilterProfilesByAdvancedParamsFilters = {
  selectedMetric?: string;
  optimizationClass?: string;
  gpuModel?: string;
  precision?: string;
  gpuCount?: string;
};

/**
 * Narrows service templates for the profile dropdown using metric + advanced profile fields.
 *
 * **Automatic** (`ADVANCED_PARAM_AUTOMATIC`): that control is not used to filter; deploy may
 * choose automatically for that dimension. A field is also treated as automatic when empty.
 *
 * **Order of checks** (template is excluded on first failed check):
 * 1. Metric — if the user selected a metric, `status.profile.metadata.metric` must match.
 * 2. If optimization class, GPU, precision, and GPU count are all automatic → keep any template that passed (1).
 * 3. Otherwise require equality on each non-automatic field vs `metadata`: type (optimization class),
 *    GPU model, precision, GPU count (count compared as string to form value).
 */
export function filterProfilesByAdvancedParams(
  profiles: AIMClusterServiceTemplate[],
  filters: FilterProfilesByAdvancedParamsFilters,
): AIMClusterServiceTemplate[] {
  const isAutomatic = (v: string | undefined) =>
    !v || v === ADVANCED_PARAM_AUTOMATIC;
  const matchesOrAutomatic = (
    selected: string | undefined,
    actual: string | undefined,
  ) => isAutomatic(selected) || actual === selected;

  const { selectedMetric, optimizationClass, gpuModel, precision, gpuCount } =
    filters;

  const allFiltersAutomatic =
    isAutomatic(optimizationClass) &&
    isAutomatic(gpuModel) &&
    isAutomatic(precision) &&
    isAutomatic(gpuCount);

  const metricFiltered = profiles.filter((t) => {
    if (!selectedMetric || selectedMetric === '') return true;
    return t.status?.profile?.metadata?.metric === selectedMetric;
  });

  if (allFiltersAutomatic) return metricFiltered;

  return metricFiltered.filter((t) => {
    const meta = t.status?.profile?.metadata;
    return (
      matchesOrAutomatic(optimizationClass, meta?.type) &&
      matchesOrAutomatic(gpuModel, meta?.gpu) &&
      matchesOrAutomatic(precision, meta?.precision) &&
      (isAutomatic(gpuCount) || String(meta?.gpuCount) === gpuCount)
    );
  });
}
