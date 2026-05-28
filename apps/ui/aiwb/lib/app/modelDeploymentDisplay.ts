// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { TFunction } from 'i18next';

export type ModelProfileSubtitleInput = {
  imageVersion?: string;
  metric?: string;
  gpu?: string | null;
  templateGpuCount?: number | null;
  precision?: string | null;
};

/** Same GPU count label as tables and {@link ModelProfileSummary} (e.g. 8x GPU). */
export function formatTemplateGpuCount(count: number): string {
  return `${count}x GPU`;
}

/** Subtitle line for model deployment selects (version · metric · hardware · …). */
export function formatModelDeploymentSubtitle(
  t: TFunction,
  info: ModelProfileSubtitleInput,
): string {
  const metricLabel = info.metric
    ? t(`performanceMetrics.values.${info.metric}`, {
        ns: 'models',
        defaultValue: info.metric,
      })
    : '';
  const countPart =
    info.templateGpuCount != null
      ? formatTemplateGpuCount(info.templateGpuCount)
      : null;
  const parts = [
    info.imageVersion,
    metricLabel,
    info.gpu,
    countPart,
    info.precision,
  ].filter((p): p is string => Boolean(p && String(p).trim() !== ''));
  return parts.join(' · ');
}
