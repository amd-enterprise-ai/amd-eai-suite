// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Workload } from '@amdenterpriseai/types/src';
import { AIMService } from './aims';

export type ChattableResponse = {
  aimServices: AIMService[];
  workloads: Workload[];
};

export enum ChatWorkloadType {
  AIMService = 'aimservice',
  Workload = 'workload',
}
