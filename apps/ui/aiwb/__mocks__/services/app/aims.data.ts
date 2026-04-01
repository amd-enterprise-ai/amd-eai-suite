// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  AIMServiceStatus,
  AIMStatus,
  AIMWorkloadStatus,
  ParsedAIM,
  AggregatedAIM,
} from '@/types/aims';

export const mockAims: ParsedAIM[] = [
  {
    description: {
      short: 'A large language model for text generation',
      full: 'Llama 2 is a family of large language models that use an optimized transformer architecture.',
    },
    title: 'Llama 2 7B',
    imageVersion: '2.0.1',
    canonicalName: 'meta-llama/llama-2-7b',
    tags: ['llm', 'text-generation', 'chat'],
    status: AIMStatus.READY,
    workloadStatuses: [AIMWorkloadStatus.DEPLOYED],
    isPreview: false,
    isHfTokenRequired: true,
    model: 'aim-llama-2-7b-v2',
    resourceName: 'aim-llama-2-7b-v2',
    anotations: {
      aimEaiAmdComSourceRegistry: 'docker.io',
      aimEaiAmdComSourceRepository: 'amdenterpriseai/aim-meta-llama-llama-2-7b',
      aimEaiAmdComSourceTag: '2.0.1',
    },
    imageReference: 'docker.io/amdenterpriseai/aim-meta-llama-llama-2-7b:2.0.1',
    deployedService: {
      id: 'service-1',
      metadata: {
        name: 'llama-2-7b-service',
        namespace: 'test-namespace',
        uid: 'uid-1',
        labels: {},
        annotations: {},
        creationTimestamp: '2023-01-01T00:00:00Z',
        ownerReferences: [],
      },
      spec: {
        model: {
          name: 'aim-llama-2-7b-v2',
        },
        replicas: 1,
        overrides: { metric: 'latency' },
        cacheModel: true,
        routing: {
          annotations: {},
          enabled: true,
        },
        runtimeConfigName: 'default-runtime',
        template: {},
      },
      status: {
        status: AIMServiceStatus.RUNNING,
        routing: {
          path: '/test-namespace/service-1',
        },
      },
      resourceName: 'llama-2-7b-service',
      clusterAuthGroupId: null,
      endpoints: {
        internal: 'http://llama-2-7b-service.test-namespace.svc.cluster.local',
        external: 'https://api.example.com/test-namespace/service-1',
      },
    },
    deployedServices: [
      {
        id: 'service-1',
        metadata: {
          name: 'llama-2-7b-service',
          namespace: 'test-namespace',
          uid: 'uid-1',
          labels: {},
          annotations: {},
          creationTimestamp: '2023-01-01T00:00:00Z',
          ownerReferences: [],
        },
        spec: {
          model: {
            name: 'aim-llama-2-7b-v2',
          },
          replicas: 1,
          overrides: { metric: 'latency' },
          cacheModel: true,
          routing: {
            annotations: {},
            enabled: true,
          },
          runtimeConfigName: 'default-runtime',
          template: {},
        },
        status: {
          status: AIMServiceStatus.RUNNING,
          routing: {
            path: '/test-namespace/service-1',
          },
        },
        resourceName: 'llama-2-7b-service',
        clusterAuthGroupId: null,
        endpoints: {
          internal:
            'http://llama-2-7b-service.test-namespace.svc.cluster.local',
          external: 'https://api.example.com/test-namespace/service-1',
        },
      },
    ],
  },
  {
    description: {
      short: 'A large language model for text generation',
      full: 'Llama 2 is a family of large language models that use an optimized transformer architecture.',
    },
    title: 'Llama 2 7B',
    imageVersion: '1.5.0',
    canonicalName: 'meta-llama/llama-2-7b',
    tags: ['llm', 'text-generation', 'chat'],
    status: AIMStatus.READY,
    workloadStatuses: [],
    isPreview: false,
    isHfTokenRequired: true,
    model: 'aim-llama-2-7b-v1',
    resourceName: 'aim-llama-2-7b-v1',
    anotations: {
      aimEaiAmdComSourceRegistry: 'docker.io',
      aimEaiAmdComSourceRepository: 'amdenterpriseai/aim-meta-llama-llama-2-7b',
      aimEaiAmdComSourceTag: '1.5.0',
    },
    imageReference: 'docker.io/amdenterpriseai/aim-meta-llama-llama-2-7b:1.5.0',
    deployedServices: [],
  },
  {
    description: {
      short: 'Text to image generation model',
      full: 'Stable Diffusion XL is a powerful text-to-image model.',
    },
    title: 'Stable Diffusion XL',
    imageVersion: '1.0.0',
    canonicalName: 'stabilityai/stable-diffusion-xl',
    tags: ['image-generation', 'diffusion'],
    status: AIMStatus.READY,
    workloadStatuses: [],
    isPreview: false,
    isHfTokenRequired: false,
    model: 'aim-stable-diffusion-xl',
    resourceName: 'aim-stable-diffusion-xl',
    anotations: {
      aimEaiAmdComSourceRegistry: 'docker.io',
      aimEaiAmdComSourceRepository:
        'amdenterpriseai/aim-stabilityai-stable-diffusion-xl',
      aimEaiAmdComSourceTag: '1.0.0',
    },
    imageReference:
      'docker.io/amdenterpriseai/aim-stabilityai-stable-diffusion-xl:1.0.0',
    deployedServices: [],
  },
  {
    description: {
      short: 'Object detection model',
      full: 'A vision model for detecting objects in images.',
    },
    title: 'Vision Detection Model',
    imageVersion: '2.0.0-preview',
    canonicalName: 'detection-model',
    tags: ['vision', 'object-detection'],
    status: AIMStatus.READY,
    workloadStatuses: [AIMWorkloadStatus.PENDING],
    isPreview: true,
    isHfTokenRequired: false,
    model: 'aim-detection-model',
    resourceName: 'aim-detection-model',
    anotations: {
      aimEaiAmdComSourceRegistry: 'docker.io',
      aimEaiAmdComSourceRepository: 'amdenterpriseai/aim-detection-model',
      aimEaiAmdComSourceTag: '2.0.0-preview',
    },
    imageReference:
      'docker.io/amdenterpriseai/aim-detection-model:2.0.0-preview',
    deployedService: {
      id: 'service-3',
      metadata: {
        name: 'detection-model-service',
        namespace: 'test-namespace',
        uid: 'uid-3',
        labels: {},
        annotations: {},
        creationTimestamp: '2023-01-03T00:00:00Z',
        ownerReferences: [],
      },
      spec: {
        model: {
          name: 'aim-detection-model',
        },
        replicas: 1,
        overrides: {},
        cacheModel: true,
        routing: {
          annotations: {},
          enabled: true,
        },
        runtimeConfigName: 'default-runtime',
        template: {},
      },
      status: {
        status: AIMServiceStatus.PENDING,
      },
      resourceName: 'detection-model-service',
      clusterAuthGroupId: null,
      endpoints: {
        internal: '',
        external: '',
      },
    },
    deployedServices: [
      {
        id: 'service-3',
        metadata: {
          name: 'detection-model-service',
          namespace: 'test-namespace',
          uid: 'uid-3',
          labels: {},
          annotations: {},
          creationTimestamp: '2023-01-03T00:00:00Z',
          ownerReferences: [],
        },
        spec: {
          model: {
            name: 'aim-detection-model',
          },
          replicas: 1,
          overrides: {},
          cacheModel: true,
          routing: {
            annotations: {},
            enabled: true,
          },
          runtimeConfigName: 'default-runtime',
          template: {},
        },
        status: {
          status: AIMServiceStatus.PENDING,
        },
        resourceName: 'detection-model-service',
        clusterAuthGroupId: null,
        endpoints: {
          internal: '',
          external: '',
        },
      },
    ],
  },
];

// Aggregated AIM with multiple versions and deployments
const mockLlamaParsedAims: ParsedAIM[] = [
  { ...mockAims[0], isLatest: true },
  { ...mockAims[1], isLatest: false },
];
export const mockAggregatedAims: AggregatedAIM[] = [
  {
    repository: 'amdenterpriseai/aim-meta-llama-llama-2-7b',
    parsedAIMs: mockLlamaParsedAims,
    latestAim: mockLlamaParsedAims[0]!,
    isSupported: true,
    deploymentCounts: {
      [AIMWorkloadStatus.DEPLOYED]: 1,
      [AIMWorkloadStatus.DEGRADED]: 0,
      [AIMWorkloadStatus.PENDING]: 0,
      [AIMWorkloadStatus.FAILED]: 0,
      [AIMWorkloadStatus.NOT_DEPLOYED]: 0,
      [AIMWorkloadStatus.DELETED]: 0,
    },
    aggregated: {
      title: 'Llama 2 7B',
      aiLabName: 'Meta',
      canonicalName: 'meta-llama/llama-2-7b',
      latestImageVersion: '2.0.1',
      isHfTokenRequired: true,
      tags: ['llm', 'text-generation', 'chat'],
      description: {
        short: 'A large language model for text generation',
        full: 'Llama 2 is a family of large language models that use an optimized transformer architecture.',
      },
    },
  },
  (() => {
    const sdParsedAims = [{ ...mockAims[2], isLatest: true }];
    return {
      repository: 'amdenterpriseai/aim-stabilityai-stable-diffusion-xl',
      parsedAIMs: sdParsedAims,
      latestAim: sdParsedAims[0],
      isSupported: true,
      deploymentCounts: {
        [AIMWorkloadStatus.DEPLOYED]: 0,
        [AIMWorkloadStatus.DEGRADED]: 0,
        [AIMWorkloadStatus.PENDING]: 0,
        [AIMWorkloadStatus.FAILED]: 0,
        [AIMWorkloadStatus.NOT_DEPLOYED]: 0,
        [AIMWorkloadStatus.DELETED]: 0,
      },
      aggregated: {
        title: 'Stable Diffusion XL',
        aiLabName: 'stabilityai',
        canonicalName: 'stabilityai/stable-diffusion-xl',
        latestImageVersion: '1.0.0',
        isHfTokenRequired: false,
        tags: ['image-generation', 'diffusion'],
        description: {
          short: 'Text to image generation model',
          full: 'Stable Diffusion XL is a powerful text-to-image model.',
        },
      },
    };
  })(),
  (() => {
    const detectionParsedAims = [{ ...mockAims[3], isLatest: true }];
    return {
      repository: 'amdenterpriseai/aim-detection-model',
      parsedAIMs: detectionParsedAims,
      latestAim: detectionParsedAims[0],
      isSupported: true,
      deploymentCounts: {
        [AIMWorkloadStatus.DEPLOYED]: 0,
        [AIMWorkloadStatus.DEGRADED]: 0,
        [AIMWorkloadStatus.PENDING]: 1,
        [AIMWorkloadStatus.FAILED]: 0,
        [AIMWorkloadStatus.NOT_DEPLOYED]: 0,
        [AIMWorkloadStatus.DELETED]: 0,
      },
      aggregated: {
        title: 'Vision Detection Model',
        aiLabName: 'detection-model',
        canonicalName: 'detection-model',
        latestImageVersion: '2.0.0-preview',
        isHfTokenRequired: false,
        tags: ['vision', 'object-detection'],
        description: {
          short: 'Object detection model',
          full: 'A vision model for detecting objects in images.',
        },
      },
    };
  })(),
];

// Mock with multiple deployments of the same model
const mockMultiDeployParsedAims = [
  {
    ...mockAims[0],
    deployedServices: [
      {
        id: 'service-1',
        metadata: {
          name: 'llama-deployment-1',
          namespace: 'test-namespace',
          uid: 'uid-1',
          labels: {},
          annotations: {},
          creationTimestamp: '2023-01-01T00:00:00Z',
          ownerReferences: [],
        },
        spec: {
          model: {
            name: 'aim-llama-2-7b-v2',
          },
          replicas: 1,
          overrides: { metric: 'latency' },
          cacheModel: true,
          routing: {
            annotations: {},
            enabled: true,
          },
          runtimeConfigName: 'default-runtime',
          template: {},
        },
        status: {
          status: AIMServiceStatus.RUNNING,
          routing: {
            path: '/test-namespace/service-1',
          },
        },
        resourceName: 'llama-deployment-1',
        clusterAuthGroupId: null,
        endpoints: {
          internal:
            'http://llama-deployment-1.test-namespace.svc.cluster.local',
          external: 'https://api.example.com/test-namespace/service-1',
        },
      },
      {
        id: 'service-2',
        metadata: {
          name: 'llama-deployment-2',
          namespace: 'test-namespace',
          uid: 'uid-2',
          labels: {},
          annotations: {},
          creationTimestamp: '2023-01-02T00:00:00Z',
          ownerReferences: [],
        },
        spec: {
          model: {
            name: 'aim-llama-2-7b-v2',
          },
          replicas: 1,
          overrides: { metric: 'throughput' },
          cacheModel: true,
          routing: {
            annotations: {},
            enabled: true,
          },
          runtimeConfigName: 'default-runtime',
          template: {},
        },
        status: {
          status: AIMServiceStatus.PENDING,
          routing: {
            path: '/test-namespace/service-2',
          },
        },
        resourceName: 'llama-deployment-2',
        clusterAuthGroupId: null,
        endpoints: {
          internal:
            'http://llama-deployment-2.test-namespace.svc.cluster.local',
          external: 'https://api.example.com/test-namespace/service-2',
        },
      },
    ],
    workloadStatuses: [AIMWorkloadStatus.DEPLOYED, AIMWorkloadStatus.PENDING],
    isLatest: true,
  },
];
export const mockAggregatedAimWithMultipleDeployments: AggregatedAIM = {
  repository: 'amdenterpriseai/aim-meta-llama-llama-2-7b',
  isSupported: true,
  parsedAIMs: mockMultiDeployParsedAims,
  latestAim: mockMultiDeployParsedAims[0],
  deploymentCounts: {
    [AIMWorkloadStatus.DEPLOYED]: 1,
    [AIMWorkloadStatus.DEGRADED]: 0,
    [AIMWorkloadStatus.PENDING]: 1,
    [AIMWorkloadStatus.FAILED]: 0,
    [AIMWorkloadStatus.NOT_DEPLOYED]: 0,
    [AIMWorkloadStatus.DELETED]: 0,
  },
  aggregated: {
    title: 'Llama 2 7B',
    aiLabName: 'Meta',
    canonicalName: 'meta-llama/llama-2-7b',
    latestImageVersion: '2.0.1',
    isHfTokenRequired: true,
    tags: ['llm', 'text-generation', 'chat'],
    description: {
      short: 'A large language model for text generation',
      full: 'Llama 2 is a family of large language models that use an optimized transformer architecture.',
    },
  },
};

const mockUnsupportedParsedAims = [
  {
    description: {
      short: 'An unsupported model',
      full: 'This model is not compatible with current cluster hardware.',
    },
    title: 'Unsupported Model',
    imageVersion: '1.0.0',
    canonicalName: 'unsupported/model',
    tags: ['llm'],
    status: AIMStatus.NOT_AVAILABLE,
    workloadStatuses: [AIMWorkloadStatus.NOT_DEPLOYED],
    isPreview: false,
    isHfTokenRequired: false,
    model: 'aim-unsupported-model',
    resourceName: 'aim-unsupported-model',
    anotations: {
      aimEaiAmdComSourceRegistry: 'docker.io',
      aimEaiAmdComSourceRepository: 'amdenterpriseai/aim-unsupported-model',
      aimEaiAmdComSourceTag: '1.0.0',
    },
    imageReference: 'docker.io/amdenterpriseai/aim-unsupported-model:1.0.0',
    deployedServices: [],
    isLatest: true,
  },
];
export const mockUnsupportedAggregatedAim: AggregatedAIM = {
  repository: 'amdenterpriseai/aim-unsupported-model',
  isSupported: false,
  parsedAIMs: mockUnsupportedParsedAims,
  latestAim: null,
  deploymentCounts: {
    [AIMWorkloadStatus.DEPLOYED]: 0,
    [AIMWorkloadStatus.DEGRADED]: 0,
    [AIMWorkloadStatus.PENDING]: 0,
    [AIMWorkloadStatus.FAILED]: 0,
    [AIMWorkloadStatus.NOT_DEPLOYED]: 0,
    [AIMWorkloadStatus.DELETED]: 0,
  },
  aggregated: {
    title: 'Unsupported Model',
    aiLabName: 'unsupported',
    canonicalName: 'unsupported/model',
    latestImageVersion: '1.0.0',
    isHfTokenRequired: false,
    tags: ['llm'],
    description: {
      short: 'An unsupported model',
      full: 'This model is not compatible with current cluster hardware.',
    },
  },
};

const mockMixedSupportParsedAims = [
  {
    description: {
      short: 'A mixed support model',
      full: 'Some versions of this model are supported, others are not.',
    },
    title: 'Mixed Support Model',
    imageVersion: '2.0.0',
    canonicalName: 'mixed/model',
    tags: ['llm'],
    status: AIMStatus.READY,
    workloadStatuses: [AIMWorkloadStatus.NOT_DEPLOYED],
    isPreview: false,
    isHfTokenRequired: false,
    model: 'aim-mixed-v2',
    resourceName: 'aim-mixed-v2',
    anotations: {
      aimEaiAmdComSourceRegistry: 'docker.io',
      aimEaiAmdComSourceRepository: 'amdenterpriseai/aim-mixed-support-model',
      aimEaiAmdComSourceTag: '2.0.0',
    },
    imageReference: 'docker.io/amdenterpriseai/aim-mixed-support-model:2.0.0',
    deployedServices: [],
    isLatest: true,
  },
  {
    description: {
      short: 'A mixed support model',
      full: 'Some versions of this model are supported, others are not.',
    },
    title: 'Mixed Support Model',
    imageVersion: '1.0.0',
    canonicalName: 'mixed/model',
    tags: ['llm'],
    status: AIMStatus.NOT_AVAILABLE,
    workloadStatuses: [AIMWorkloadStatus.NOT_DEPLOYED],
    isPreview: false,
    isHfTokenRequired: false,
    model: 'aim-mixed-v1',
    resourceName: 'aim-mixed-v1',
    anotations: {
      aimEaiAmdComSourceRegistry: 'docker.io',
      aimEaiAmdComSourceRepository: 'amdenterpriseai/aim-mixed-support-model',
      aimEaiAmdComSourceTag: '1.0.0',
    },
    imageReference: 'docker.io/amdenterpriseai/aim-mixed-support-model:1.0.0',
    deployedServices: [],
    isLatest: false,
  },
];
export const mockMixedSupportAggregatedAim: AggregatedAIM = {
  repository: 'amdenterpriseai/aim-mixed-support-model',
  isSupported: true,
  parsedAIMs: mockMixedSupportParsedAims,
  latestAim: mockMixedSupportParsedAims[0],
  deploymentCounts: {
    [AIMWorkloadStatus.DEPLOYED]: 0,
    [AIMWorkloadStatus.DEGRADED]: 0,
    [AIMWorkloadStatus.PENDING]: 0,
    [AIMWorkloadStatus.FAILED]: 0,
    [AIMWorkloadStatus.NOT_DEPLOYED]: 0,
    [AIMWorkloadStatus.DELETED]: 0,
  },
  aggregated: {
    title: 'Mixed Support Model',
    aiLabName: 'mixed',
    canonicalName: 'mixed/model',
    latestImageVersion: '2.0.0',
    isHfTokenRequired: false,
    tags: ['llm'],
    description: {
      short: 'A mixed support model',
      full: 'Some versions of this model are supported, others are not.',
    },
  },
};
