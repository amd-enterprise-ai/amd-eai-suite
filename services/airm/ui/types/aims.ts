// Copyright © Advanced Micro Devices, Inc., or its affiliates.

// SPDX-License-Identifier: MIT

import { Workload } from './workloads';

export enum AimWorkloadStatus {
  DEPLOYED = 'deployed',
  NOT_DEPLOYED = 'not_deployed',
  PENDING = 'pending',
}

export type Aim = {
  id: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
  imageName: string;
  imageTag: string;
  image: string;

  labels: {
    [key: string]: string;
  };

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
};
