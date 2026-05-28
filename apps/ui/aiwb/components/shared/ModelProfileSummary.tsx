// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { TFunction } from 'i18next';

import { formatTemplateGpuCount } from '@/lib/app/modelDeploymentDisplay';

export type ModelProfileSummaryFields = {
  metric?: string | null;
  gpu?: string | null;
  templateGpuCount?: number | null;
  precision?: string | null;
};

type Props = {
  profile: ModelProfileSummaryFields | null | undefined;
  t: TFunction;
};

/** Second line under deployment name: translated metric · GPU model · GPU count · precision. */
export function ModelProfileSummary({ profile, t }: Props) {
  if (!profile) {
    return null;
  }
  const parts: string[] = [];
  if (profile.metric) {
    parts.push(
      t(`models:performanceMetrics.values.${profile.metric}`, {
        defaultValue: profile.metric,
      }),
    );
  }
  if (profile.gpu) {
    parts.push(profile.gpu);
  }
  if (profile.templateGpuCount != null) {
    parts.push(formatTemplateGpuCount(profile.templateGpuCount));
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
