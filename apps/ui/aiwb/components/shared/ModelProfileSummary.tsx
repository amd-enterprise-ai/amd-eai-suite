// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { TFunction } from 'i18next';

import { formatTemplateGpuCount } from '@/lib/app/modelDeploymentDisplay';
import { getMetricTranslationKey } from '@/lib/app/aims';
import type { AIMProfileSpec, AIMService } from '@/types/aims';

export type ModelProfileSummaryFields = {
  metric?: string | null;
  gpu?: string | null;
  templateGpuCount?: number | null;
  acceleratorType?: string | null;
  precision?: string | null;
};

/**
 * Projects an AIMService's resolved-profile spec into the shape consumed by
 * `ModelProfileSummary` and `modelDeploymentDisplay`.
 *
 * The aim-engine status only carries the resolved profile's *name*; AIWB no
 * longer enriches the spec on the service response. Callers pass a
 * name → spec lookup built from the AIMProfile catalog endpoints — typically
 * via the `useProfileSpecsForServices` hook (which wraps
 * `getAimClusterProfilesByAimIds` and `getProjectAimProfilesByAimIds`).
 *
 * Returns null when the engine hasn't stamped `resolvedProfile` yet, or when
 * the referenced profile isn't in the supplied catalog (e.g. an engine-owned
 * overlay copy from `spec.profileOverrides`).
 */
export function toProfileSummaryFields(
  service: AIMService | undefined | null,
  profileSpecByName: Map<string, AIMProfileSpec> | null | undefined,
): ModelProfileSummaryFields | null {
  const name = service?.status.resolvedProfile?.name;
  if (!name || !profileSpecByName) return null;
  const spec = profileSpecByName.get(name);
  if (!spec) return null;
  return {
    metric: spec.metric ?? null,
    gpu: spec.acceleratorModel ?? null,
    templateGpuCount: spec.acceleratorCount ?? null,
    acceleratorType: spec.acceleratorType ?? null,
    precision: spec.precision ?? null,
  };
}

type Props = {
  profile: ModelProfileSummaryFields | null | undefined;
  t: TFunction<'models'>;
};

/** Second line under deployment name: translated metric · GPU model · GPU count · precision. */
export function ModelProfileSummary({ profile, t }: Props) {
  if (!profile) {
    return null;
  }
  const parts: string[] = [];
  if (profile.metric) {
    parts.push(
      String(
        t(getMetricTranslationKey(profile.metric), {
          defaultValue: profile.metric,
        }),
      ),
    );
  }
  if (profile.gpu) {
    parts.push(profile.gpu);
  }
  if (profile.templateGpuCount != null) {
    parts.push(
      formatTemplateGpuCount(profile.templateGpuCount, profile.acceleratorType),
    );
  }
  if (profile.precision) {
    parts.push(profile.precision);
  }
  if (parts.length === 0) {
    return null;
  }
  return (
    <span className="flex flex-wrap items-center gap-x-[10px] text-tiny text-default-500">
      {parts.map((part, index) => (
        <span key={`${part}-${index}`}>
          {part}
          {index < parts.length - 1 ? ' ·' : ''}
        </span>
      ))}
    </span>
  );
}
