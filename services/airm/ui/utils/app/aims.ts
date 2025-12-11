// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  type Aim,
  type ParsedAim,
  type RecommendedDeployment,
  AimWorkloadStatus,
} from '@/types/aims';
import { WorkloadStatus } from '@/types/enums/workloads';

/**
 * Parses an Aim object to extract structured information from its labels and determine workload status.
 *
 * @param {Aim} aim - The aim object to parse.
 * @returns {ParsedAim} The parsed aim data with extracted description, version, tags, and status.
 */
export const aimParser = (aim: Aim): ParsedAim => {
  // Check if imageTag has preview suffix (-dev, -rc, or -preview)
  const isPreview = /-(?:dev|rc|preview)(?:$|\.)/.test(aim.imageTag);

  const parsedAim: ParsedAim = {
    description: {
      short: '',
      full: '',
    },
    imageVersion: '',
    title: '',
    tags: [],
    canonicalName: '',
    workloadStatus: AimWorkloadStatus.NOT_DEPLOYED,
    isPreview,
    isHfTokenRequired: false,
    recommendedDeployments: [],
    availableMetrics: [],
  };

  for (const key in aim.labels) {
    const lowerKey = key.toLowerCase();

    if (
      lowerKey.includes('description') &&
      (lowerKey.includes('short') ||
        (!lowerKey.includes('full') && lowerKey.endsWith('description')))
    ) {
      parsedAim.description.short = aim.labels[key];
    } else if (lowerKey.includes('description') && lowerKey.includes('full')) {
      parsedAim.description.full = aim.labels[key];
    } else if (lowerKey.includes('image') && lowerKey.includes('title')) {
      parsedAim.title = aim.labels[key];
    } else if (lowerKey.includes('title') && !lowerKey.includes('image')) {
      parsedAim.title = aim.labels[key];
    } else if (lowerKey.includes('image') && lowerKey.includes('version')) {
      parsedAim.imageVersion = aim.labels[key];
    } else if (lowerKey.includes('model') && lowerKey.includes('tags')) {
      parsedAim.tags = aim.labels[key].split(',').map((tag) => tag.trim());
    } else if (
      lowerKey.includes('model') &&
      lowerKey.includes('canonicalname')
    ) {
      parsedAim.canonicalName = aim.labels[key];
    } else if (lowerKey.includes('hftoken') && lowerKey.includes('required')) {
      parsedAim.isHfTokenRequired = aim.labels[key].toLowerCase() === 'true';
    }
  }

  // Use recommendedDeployments parsed by backend
  parsedAim.recommendedDeployments = aim.recommendedDeployments || [];

  // Extract unique metrics from recommendedDeployments
  parsedAim.availableMetrics = Array.from(
    new Set(
      parsedAim.recommendedDeployments
        .map((d: RecommendedDeployment) => d.metric)
        .filter(Boolean),
    ),
  );

  // Determine workload status
  const hasWorkload = !!aim.workload;
  const workloadStatus = aim.workload?.status;
  const isPending =
    workloadStatus === WorkloadStatus.PENDING ||
    workloadStatus === WorkloadStatus.DELETING;

  if (hasWorkload && workloadStatus === WorkloadStatus.RUNNING) {
    parsedAim.workloadStatus = AimWorkloadStatus.DEPLOYED;
  } else if (hasWorkload && isPending) {
    parsedAim.workloadStatus = AimWorkloadStatus.PENDING;
  } else {
    parsedAim.workloadStatus = AimWorkloadStatus.NOT_DEPLOYED;
  }

  return parsedAim;
};

/**
 * Parses an array of Aim objects to extract structured information from their labels and determine workload status.
 * Filters out aims with empty titles.
 *
 * @param {Aim[]} aims - The array of aim objects to parse.
 * @returns {Aim[]} The array of aims with parsed data merged in, excluding those with empty titles.
 */
export const aimsParser = (aims: Aim[]): Aim[] => {
  return aims.reduce<Aim[]>((acc, aim) => {
    const parsed = aimParser(aim);
    if (parsed.title !== '') {
      acc.push({ ...aim, ...parsed });
    }
    return acc;
  }, []);
};
