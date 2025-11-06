// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Model, ModelOnboardingStatus } from '@/types/models';

/**
 * Mock data for models to be used in tests
 */
export const mockModels: Model[] = [
  {
    id: '1',
    name: 'model-1',
    createdAt: '2023-01-01T00:00:00Z',
    modelWeightsPath: '/dev/null',
    createdBy: 'Test',
    onboardingStatus: ModelOnboardingStatus.READY,
    canonicalName: 'org/model-1',
  },
  {
    id: '2',
    name: 'model-2',
    createdAt: '2023-01-02T00:00:00Z',
    modelWeightsPath: '/dev/null',
    createdBy: 'Test',
    onboardingStatus: ModelOnboardingStatus.PENDING,
    canonicalName: 'org/model-2',
  },
  {
    id: '3',
    name: 'model-3',
    createdAt: '2023-01-02T00:00:00Z',
    modelWeightsPath: '/dev/null',
    createdBy: 'Test',
    canonicalName: 'org/model-3',
    onboardingStatus: ModelOnboardingStatus.READY,
  },
  {
    id: '4',
    name: 'model-4',
    createdAt: '2023-01-02T00:00:00Z',
    modelWeightsPath: '/dev/null',
    createdBy: 'Test',
    canonicalName: 'org/model-4',
    onboardingStatus: ModelOnboardingStatus.FAILED,
  },
  {
    id: '5',
    name: 'model-5',
    createdAt: '2023-01-01T00:00:00Z',
    modelWeightsPath: '/dev/null',
    createdBy: 'Test',
    onboardingStatus: ModelOnboardingStatus.READY,
    canonicalName: 'org/model-5',
  },
  {
    id: '6',
    name: 'model-6',
    createdAt: '2023-01-01T00:00:00Z',
    modelWeightsPath: '/dev/null',
    createdBy: 'Test',
    onboardingStatus: ModelOnboardingStatus.READY,
    canonicalName: 'org/model-6',
  },
];
