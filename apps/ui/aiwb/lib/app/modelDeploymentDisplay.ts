// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { TFunction } from 'i18next';
import { getMetricTranslationKey } from './aims';

export type ModelProfileSubtitleInput = {
  imageVersion?: string;
  metric?: string;
  gpu?: string | null;
  templateGpuCount?: number | null;
  acceleratorType?: string | null;
  precision?: string | null;
};

/** Same accelerator count label as tables and {@link ModelProfileSummary} (e.g. 8x GPU, 8x CPU). */
export function formatTemplateGpuCount(
  count: number,
  acceleratorType?: string | null,
): string {
  return acceleratorType?.trim().toLowerCase() === 'cpu'
    ? `${count}x CPU`
    : `${count}x GPU`;
}

/** Subtitle line for model deployment selects (version · metric · hardware · …). */
export function formatModelDeploymentSubtitle(
  t: TFunction<'models'>,
  info: ModelProfileSubtitleInput,
): string {
  const metricLabel = info.metric
    ? t(getMetricTranslationKey(info.metric), {
        ns: 'models',
        defaultValue: info.metric,
      })
    : '';
  const countPart =
    info.templateGpuCount != null
      ? formatTemplateGpuCount(info.templateGpuCount, info.acceleratorType)
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
