// Copyright © Advanced Micro Devices, Inc., or its affiliates.

// SPDX-License-Identifier: MIT

import { Workload } from './workloads';

export enum AimWorkloadStatus {
  DEPLOYED = 'deployed',
  NOT_DEPLOYED = 'not_deployed',
  PENDING = 'pending',
}

export enum AIMStatus {
  NOT_AVAILABLE = 'NotAvailable',
  PENDING = 'Pending',
  PROGRESSING = 'Progressing',
  READY = 'Ready',
  DEGRADED = 'Degraded',
  FAILED = 'Failed',
  DELETED = 'Deleted',
}

export type RecommendedDeployment = {
  gpuModel: string;
  gpuCount: number;
  precision: string;
  metric: string;
  description: string;
};

export type Aim = {
  id: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
  imageName: string;
  imageTag: string;
  image: string;
  status: string;

  labels: {
    [key: string]: string;
  };

  // Parsed by backend from labels
  recommendedDeployments: RecommendedDeployment[];

  workload?: Workload;
} & ParsedAim;

export type ParsedAim = {
  description: {
    short: string;
    full: string;
  };
  title: string;
  imageVersion: string;
  canonicalName: string;
  tags: string[];
  workloadStatus: AimWorkloadStatus;
  isPreview: boolean;
  isHfTokenRequired: boolean;
  recommendedDeployments: RecommendedDeployment[];
  availableMetrics: string[];
};

export type AimDeployPayload = {
  imagePullSecrets?: string[];
  hfToken?: string;
  metric?: string;
  cacheModel: boolean;
  replicas: number;
  allowUnoptimized: boolean;
};
