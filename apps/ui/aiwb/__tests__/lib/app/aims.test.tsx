// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  transformToAggregatedAIMs,
  resolveAILabName,
  aimParser,
  resolveAIMServiceDisplay,
  deployAim,
} from '@/lib/app/aims';
import {
  AIMDeployPayload,
  AIMServiceStatus,
  AIMStatus,
  AIMWorkloadStatus,
  ParsedAIM,
  AIMClusterModel,
  AIMService,
  AIMMetric,
} from '@/types/aims';

describe('aims utility functions', () => {
  describe('resolveAILabName', () => {
    it('maps meta-llama to Meta', () => {
      expect(resolveAILabName('meta-llama/Llama-3.1-8B')).toBe('Meta');
    });

    it('maps mistralai to Mistral AI', () => {
      expect(resolveAILabName('mistralai/Mixtral-8x7B')).toBe('Mistral AI');
    });

    it('maps Qwen to Alibaba Cloud', () => {
      expect(resolveAILabName('Qwen/Qwen-14B')).toBe('Alibaba Cloud');
    });

    it('maps CohereLabs to Cohere', () => {
      expect(resolveAILabName('CohereLabs/command-r')).toBe('Cohere');
    });

    it('maps openai to OpenAI', () => {
      expect(resolveAILabName('openai/gpt-4')).toBe('OpenAI');
    });

    it('returns prefix as-is for unknown labs', () => {
      expect(resolveAILabName('unknown-lab/model-name')).toBe('unknown-lab');
    });

    it('handles model names without slash', () => {
      expect(resolveAILabName('standalone-model')).toBe('standalone-model');
    });
  });

  describe('resolveAIMServiceDisplay', () => {
    const createMockAIMService = (
      overrides: Partial<{
        id: string | null;
        'spec.model.name': string;
        'spec.overrides.metric': string;
      }> = {},
    ): AIMService => {
      const modelName = overrides['spec.model.name'] ?? 'aim-test-model';
      return {
        id: overrides.id ?? 'aim-1',
        metadata: {
          name: 'aim-1',
          namespace: 'project1',
          uid: 'uid-1',
          labels: {},
          annotations: {},
          creationTimestamp: '',
          ownerReferences: [],
        },
        spec: {
          model: { name: modelName },
          replicas: 1,
          overrides: {
            metric: overrides['spec.overrides.metric'],
          },
          cacheModel: false,
          routing: { annotations: {}, enabled: false },
          runtimeConfigName: '',
          template: {},
        },
        status: {
          status: AIMServiceStatus.RUNNING,
          resolvedModel: { name: modelName },
          routing: { path: '' },
          endpoints: { internal: '', external: '' },
        },
        resourceName: modelName,
        clusterAuthGroupId: null,
        endpoints: { internal: '', external: '' },
      } as AIMService;
    };

    const createMockParsedAIM = (
      overrides: Partial<ParsedAIM> = {},
    ): ParsedAIM => ({
      resourceName: 'aim-test-model',
      model: 'test-model',
      imageReference: 'img:1.0',
      anotations: {
        aimEaiAmdComSourceRegistry: '',
        aimEaiAmdComSourceRepository: '',
        aimEaiAmdComSourceTag: '',
      },
      description: { short: '', full: '' },
      title: 'Test Model Title',
      imageVersion: '1.2.3',
      canonicalName: 'org/test-model',
      tags: [],
      status: AIMStatus.READY,
      workloadStatuses: [],
      isPreview: false,
      isHfTokenRequired: false,
      ...overrides,
    });

    it('returns title, canonicalName, and imageVersion from matching ParsedAIM', () => {
      const aimService = createMockAIMService();
      const parsedAIMs = [
        createMockParsedAIM({
          resourceName: 'aim-test-model',
          title: 'Llama 3.1 8B',
          canonicalName: 'meta-llama/Llama-3.1-8B',
          imageVersion: '2.0.0',
        }),
      ];

      const result = resolveAIMServiceDisplay(aimService, parsedAIMs);

      expect(result.title).toBe('Llama 3.1 8B');
      expect(result.canonicalName).toBe('meta-llama/Llama-3.1-8B');
      expect(result.imageVersion).toBe('2.0.0');
      expect(result.resourceName).toBe('aim-test-model');
    });

    it('falls back to resourceName when no ParsedAIM matches', () => {
      const aimService = createMockAIMService({
        'spec.model.name': 'other-model',
      });
      const parsedAIMs = [
        createMockParsedAIM({ resourceName: 'aim-test-model' }),
      ];

      const result = resolveAIMServiceDisplay(aimService, parsedAIMs);

      expect(result.title).toBe('other-model');
      expect(result.canonicalName).toBe('other-model');
      expect(result.imageVersion).toBe('');
      expect(result.resourceName).toBe('other-model');
    });

    it('falls back to resourceName when parsedAIMs is undefined', () => {
      const aimService = createMockAIMService({
        'spec.model.name': 'standalone',
      });

      const result = resolveAIMServiceDisplay(aimService);

      expect(result.title).toBe('standalone');
      expect(result.canonicalName).toBe('standalone');
      expect(result.imageVersion).toBe('');
      expect(result.resourceName).toBe('standalone');
    });

    it('returns throughput metric when spec.overrides.metric is throughput', () => {
      const aimService = createMockAIMService({
        'spec.overrides.metric': 'throughput',
      });

      const result = resolveAIMServiceDisplay(aimService, []);

      expect(result.metric).toBe(AIMMetric.Throughput);
    });

    it('returns latency metric when spec.overrides.metric is latency', () => {
      const aimService = createMockAIMService({
        'spec.overrides.metric': 'latency',
      });

      const result = resolveAIMServiceDisplay(aimService, []);

      expect(result.metric).toBe(AIMMetric.Latency);
    });

    it('returns default metric when spec.overrides.metric is missing or unknown', () => {
      const aimServiceNoOverride = createMockAIMService({});
      const aimServiceUnknown = createMockAIMService({
        'spec.overrides.metric': 'unknown',
      });

      expect(resolveAIMServiceDisplay(aimServiceNoOverride, []).metric).toBe(
        AIMMetric.Default,
      );
      expect(resolveAIMServiceDisplay(aimServiceUnknown, []).metric).toBe(
        AIMMetric.Default,
      );
    });

    it('falls back to resolvedModel.name when spec.model.name is absent', () => {
      const aimService: AIMService = {
        id: 'aim-img',
        metadata: {
          name: 'qwen3-32b-custom',
          namespace: 'project1',
          uid: 'uid-img',
          labels: {},
          annotations: {},
          creationTimestamp: '',
          ownerReferences: [],
        },
        spec: {
          model: { image: 'amdenterpriseai/aim-qwen-qwen3-32b:0.8.5' },
          replicas: 1,
          overrides: {},
          cacheModel: false,
          routing: { annotations: {}, enabled: false },
          runtimeConfigName: '',
          template: {},
        },
        status: {
          status: AIMServiceStatus.RUNNING,
          resolvedModel: { name: 'aim-qwen-resolved' },
        },
        resourceName: 'qwen3-32b-custom',
        clusterAuthGroupId: null,
        endpoints: { internal: '', external: '' },
      };
      const parsedAIMs = [
        createMockParsedAIM({
          resourceName: 'aim-qwen-resolved',
          title: 'Qwen3 32B',
          canonicalName: 'qwen/Qwen3-32B',
          imageVersion: '0.8.5',
        }),
      ];

      const result = resolveAIMServiceDisplay(aimService, parsedAIMs);

      expect(result.resourceName).toBe('aim-qwen-resolved');
      expect(result.title).toBe('Qwen3 32B');
      expect(result.canonicalName).toBe('qwen/Qwen3-32B');
    });

    it('falls back to metadata.name when both model.name and resolvedModel are absent', () => {
      const aimService: AIMService = {
        id: 'aim-orphan',
        metadata: {
          name: 'orphan-service',
          namespace: 'project1',
          uid: 'uid-o',
          labels: {},
          annotations: {},
          creationTimestamp: '',
          ownerReferences: [],
        },
        spec: {
          model: { image: 'repo/model:1.0' },
          replicas: 1,
          overrides: {},
          cacheModel: false,
          routing: { annotations: {}, enabled: false },
          runtimeConfigName: '',
          template: {},
        },
        status: { status: AIMServiceStatus.PENDING },
        resourceName: 'orphan-service',
        clusterAuthGroupId: null,
        endpoints: { internal: '', external: '' },
      };

      const result = resolveAIMServiceDisplay(aimService);

      expect(result.resourceName).toBe('orphan-service');
      expect(result.title).toBe('orphan-service');
    });

    it('returns AIMServiceDisplayInfo with all required fields', () => {
      const aimService = createMockAIMService({
        'spec.model.name': 'my-aim',
        'spec.overrides.metric': 'latency',
      });
      const parsedAIMs = [
        createMockParsedAIM({
          resourceName: 'my-aim',
          title: 'My Model',
          canonicalName: 'org/my-aim',
          imageVersion: '1.0.0',
        }),
      ];

      const result = resolveAIMServiceDisplay(aimService, parsedAIMs);

      expect(result).toEqual({
        title: 'My Model',
        canonicalName: 'org/my-aim',
        imageVersion: '1.0.0',
        resourceName: 'my-aim',
        metric: AIMMetric.Latency,
      });
    });
  });

  describe('aimParser', () => {
    const createMockAIM = (
      overrides?: Partial<AIMClusterModel>,
    ): AIMClusterModel => ({
      metadata: {
        name: 'test-aim',
        namespace: null,
        uid: 'uid-123',
        labels: {},
        annotations: {
          aimEaiAmdComSourceRegistry: 'docker.io',
          aimEaiAmdComSourceRepository: 'amdenterpriseai/test-model',
          aimEaiAmdComSourceTag: '1.0.0',
        },
        creationTimestamp: '2023-01-01T00:00:00Z',
        ownerReferences: [],
      },
      spec: {
        image: 'docker.io/amdenterpriseai/test-model:1.0.0',
      },
      status: {
        status: 'Ready' as any,
        imageMetadata: {
          model: {
            canonicalName: 'test/model',
            hfTokenRequired: false,
            source: 'https://example.com',
            tags: ['test'],
            title: 'Test Model',
            variants: [],
          },
          originalLabels: {
            comAmdAimDescriptionFull: 'Full description',
            comAmdAimHfTokenRequired: 'false',
            comAmdAimModelCanonicalName: 'test/model',
            comAmdAimModelPublisher: 'Test Publisher',
            comAmdAimModelRecommendedDeployments: '[]',
            comAmdAimModelSource: 'https://example.com',
            comAmdAimModelTags: 'test',
            comAmdAimModelVariants: '',
            comAmdAimReleaseNotes: '',
            comAmdAimTitle: 'Test Model',
            orgOpencontainersImageAuthors: 'Test Author',
            orgOpencontainersImageCreated: '2023-01-01T00:00:00Z',
            orgOpencontainersImageDescription: 'Short description',
            orgOpencontainersImageDocumentation: 'https://docs.example.com',
            orgOpencontainersImageLicenses: 'MIT',
            orgOpencontainersImageRefName: '1.0.0',
            orgOpencontainersImageRevision: 'abc123',
            orgOpencontainersImageSource: 'https://github.com/example/model',
            orgOpencontainersImageTitle: 'Test Model',
            orgOpencontainersImageVendor: 'Test Vendor',
            orgOpencontainersImageVersion: '1.0.0',
          },
        },
      },
      resourceName: 'test-aim',
      ...overrides,
    });

    const createMockService = (
      status: AIMServiceStatus = AIMServiceStatus.RUNNING,
    ): AIMService => ({
      id: 'service-123',
      metadata: {
        name: 'test-service',
        namespace: 'test-namespace',
        uid: 'uid-456',
        labels: {},
        annotations: {},
        creationTimestamp: '2023-01-01T00:00:00Z',
        ownerReferences: [],
      },
      spec: {
        model: {
          name: 'test-aim',
        },
        replicas: 1,
        overrides: {},
        cacheModel: true,
        routing: {
          annotations: {},
          enabled: true,
        },
        runtimeConfigName: 'default',
        template: {},
      },
      status: {
        status,
      },
      resourceName: 'test-service',
      clusterAuthGroupId: null,
      endpoints: {
        internal: 'http://test-service.test-namespace.svc.cluster.local',
        external: 'https://api.example.com/test-namespace/service-123',
      },
    });

    it('parses AIM with no deployed services', () => {
      const aim = createMockAIM();
      const parsed = aimParser(aim);

      expect(parsed.title).toBe('Test Model');
      expect(parsed.canonicalName).toBe('test/model');
      expect(parsed.workloadStatuses).toEqual([AIMWorkloadStatus.NOT_DEPLOYED]);
      expect(parsed.deployedServices).toBeUndefined();
    });

    it('parses AIM with single deployed service', () => {
      const aim = createMockAIM();
      const service = createMockService(AIMServiceStatus.RUNNING);
      const parsed = aimParser(aim, [service]);

      expect(parsed.workloadStatuses).toEqual([AIMWorkloadStatus.DEPLOYED]);
      expect(parsed.deployedService).toEqual(service);
    });

    it('parses AIM with multiple deployed services', () => {
      const aim = createMockAIM();
      const services = [
        createMockService(AIMServiceStatus.RUNNING),
        createMockService(AIMServiceStatus.PENDING),
      ];
      const parsed = aimParser(aim, services);

      expect(parsed.workloadStatuses).toEqual([
        AIMWorkloadStatus.DEPLOYED,
        AIMWorkloadStatus.PENDING,
      ]);
      expect(parsed.deployedServices).toEqual(services);
    });

    it('maps RUNNING status to DEPLOYED', () => {
      const aim = createMockAIM();
      const service = createMockService(AIMServiceStatus.RUNNING);
      const parsed = aimParser(aim, [service]);

      expect(parsed.workloadStatuses).toContain(AIMWorkloadStatus.DEPLOYED);
    });

    it('maps PENDING status to PENDING', () => {
      const aim = createMockAIM();
      const service = createMockService(AIMServiceStatus.PENDING);
      const parsed = aimParser(aim, [service]);

      expect(parsed.workloadStatuses).toContain(AIMWorkloadStatus.PENDING);
    });

    it('maps STARTING status to PENDING', () => {
      const aim = createMockAIM();
      const service = createMockService(AIMServiceStatus.STARTING);
      const parsed = aimParser(aim, [service]);

      expect(parsed.workloadStatuses).toContain(AIMWorkloadStatus.PENDING);
    });

    it('maps FAILED status to FAILED', () => {
      const aim = createMockAIM();
      const service = createMockService(AIMServiceStatus.FAILED);
      const parsed = aimParser(aim, [service]);

      expect(parsed.workloadStatuses).toContain(AIMWorkloadStatus.FAILED);
    });

    it('maps DEGRADED status to DEGRADED', () => {
      const aim = createMockAIM();
      const service = createMockService(AIMServiceStatus.DEGRADED);
      const parsed = aimParser(aim, [service]);

      expect(parsed.workloadStatuses).toContain(AIMWorkloadStatus.DEGRADED);
    });

    it('detects preview versions with preview tag', () => {
      const aim = createMockAIM({
        status: {
          status: 'Ready' as any,
          imageMetadata: {
            model: {
              canonicalName: 'test/model',
              hfTokenRequired: false,
              source: 'https://example.com',
              tags: ['test', 'preview'],
              title: 'Test Model',
              variants: [],
            },
            originalLabels: {} as any,
          },
        },
      });
      const parsed = aimParser(aim);

      expect(parsed.isPreview).toBe(true);
    });

    it('handles empty deployedServices array', () => {
      const aim = createMockAIM();
      const parsed = aimParser(aim, []);

      expect(parsed.workloadStatuses).toEqual([AIMWorkloadStatus.NOT_DEPLOYED]);
      expect(parsed.deployedServices).toEqual([]);
    });

    it('extracts HF token requirement correctly', () => {
      const aim = createMockAIM({
        status: {
          status: 'Ready' as any,
          imageMetadata: {
            model: {
              canonicalName: 'test/model',
              hfTokenRequired: true,
              source: 'https://example.com',
              tags: ['test'],
              title: 'Test Model',
              variants: [],
            },
            originalLabels: {} as any,
          },
        },
      });
      const parsed = aimParser(aim);

      expect(parsed.isHfTokenRequired).toBe(true);
    });

    it('propagates status from AIMClusterModel', () => {
      const aim = createMockAIM({
        status: {
          status: AIMStatus.NOT_AVAILABLE,
          imageMetadata: {
            model: {
              canonicalName: 'test/model',
              hfTokenRequired: false,
              source: 'https://example.com',
              tags: ['test'],
              title: 'Test Model',
              variants: [],
            },
            originalLabels: {} as any,
          },
        },
      });
      const parsed = aimParser(aim);

      expect(parsed.status).toBe(AIMStatus.NOT_AVAILABLE);
    });

    it('sets status to Ready for supported models', () => {
      const aim = createMockAIM();
      const parsed = aimParser(aim);

      expect(parsed.status).toBe(AIMStatus.READY);
    });
  });

  describe('transformToAggregatedAIMs', () => {
    const createMockParsedAIM = (
      repository: string,
      version: string,
      overrides?: Partial<ParsedAIM>,
    ): ParsedAIM => ({
      resourceName: `aim-${version}`,
      model: `aim-${version}`,
      imageReference: `docker.io/${repository}:${version}`,
      anotations: {
        aimEaiAmdComSourceRegistry: 'docker.io',
        aimEaiAmdComSourceRepository: repository,
        aimEaiAmdComSourceTag: version,
      },
      description: {
        short: 'Test description',
        full: 'Full test description',
      },
      title: 'Test Model',
      imageVersion: version,
      canonicalName: 'test/model',
      tags: ['test'],
      status: AIMStatus.READY,
      workloadStatuses: [AIMWorkloadStatus.NOT_DEPLOYED],
      isPreview: false,
      isHfTokenRequired: false,
      ...overrides,
    });

    it('returns empty array for undefined input', () => {
      const result = transformToAggregatedAIMs(undefined);
      expect(result).toEqual([]);
    });

    it('returns empty array for empty input', () => {
      const result = transformToAggregatedAIMs([]);
      expect(result).toEqual([]);
    });

    it('groups AIMs by repository', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0'),
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0'),
        createMockParsedAIM('amdenterpriseai/model-b', '1.0.0'),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result).toHaveLength(2);
      expect(result[0].repository).toBe('amdenterpriseai/model-a');
      expect(result[0].parsedAIMs).toHaveLength(2);
      expect(result[1].repository).toBe('amdenterpriseai/model-b');
      expect(result[1].parsedAIMs).toHaveLength(1);
    });

    it('sorts versions in descending order (latest first)', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0'),
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0'),
        createMockParsedAIM('amdenterpriseai/model-a', '1.5.0'),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].parsedAIMs[0].imageVersion).toBe('2.0.0');
      expect(result[0].parsedAIMs[1].imageVersion).toBe('1.5.0');
      expect(result[0].parsedAIMs[2].imageVersion).toBe('1.0.0');
    });

    it('selects latest official release as latest (ignores preview)', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0-preview', {
          isPreview: true,
        }),
        createMockParsedAIM('amdenterpriseai/model-a', '1.5.0'),
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0'),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].latestAim!.imageVersion).toBe('1.5.0');
    });

    it('latestAim is null when no official release exists (only pre-release versions)', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0-preview', {
          isPreview: true,
        }),
        createMockParsedAIM('amdenterpriseai/model-a', '1.5.0-beta', {
          isPreview: true,
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].latestAim).toBeNull();
    });

    it('calculates deployment counts correctly', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0', {
          workloadStatuses: [AIMWorkloadStatus.DEPLOYED],
        }),
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0', {
          workloadStatuses: [
            AIMWorkloadStatus.DEPLOYED,
            AIMWorkloadStatus.PENDING,
          ],
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].deploymentCounts).toEqual({
        [AIMWorkloadStatus.DEPLOYED]: 2,
        [AIMWorkloadStatus.DEGRADED]: 0,
        [AIMWorkloadStatus.PENDING]: 1,
        [AIMWorkloadStatus.FAILED]: 0,
        [AIMWorkloadStatus.NOT_DEPLOYED]: 0,
        [AIMWorkloadStatus.DELETED]: 0,
      });
    });

    it('sets isHfTokenRequired if any version requires it', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0', {
          isHfTokenRequired: false,
        }),
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0', {
          isHfTokenRequired: true,
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].aggregated.isHfTokenRequired).toBe(true);
    });

    it('handles version strings with build metadata', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0+build.1'),
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0+build.2'),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].parsedAIMs[0].imageVersion).toBe('2.0.0+build.2');
      expect(result[0].parsedAIMs[1].imageVersion).toBe('1.0.0+build.1');
    });

    it('handles single version AIM', () => {
      const aims = [createMockParsedAIM('amdenterpriseai/model-a', '1.0.0')];

      const result = transformToAggregatedAIMs(aims);

      expect(result).toHaveLength(1);
      expect(result[0].parsedAIMs).toHaveLength(1);
      expect(result[0].latestAim!.imageVersion).toBe('1.0.0');
    });

    it('extracts AI Lab name from canonical name', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0', {
          canonicalName: 'meta-llama/Llama-3.1-8B',
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].aggregated.aiLabName).toBe('Meta');
    });

    it('uses latest version properties for aggregated data', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0', {
          title: 'Old Title',
          tags: ['old'],
        }),
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0', {
          title: 'New Title',
          tags: ['new', 'latest'],
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].aggregated.title).toBe('New Title');
      expect(result[0].aggregated.tags).toEqual(['new', 'latest']);
      expect(result[0].aggregated.latestImageVersion).toBe('2.0.0');
    });

    it('handles version sorting with different lengths', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '1.9.0'),
        createMockParsedAIM('amdenterpriseai/model-a', '1.10.0'),
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0'),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].parsedAIMs[0].imageVersion).toBe('2.0.0');
      expect(result[0].parsedAIMs[1].imageVersion).toBe('1.10.0');
      expect(result[0].parsedAIMs[2].imageVersion).toBe('1.9.0');
    });

    it('ignores beta and rc suffixes when selecting official release', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0-beta'),
        createMockParsedAIM('amdenterpriseai/model-a', '1.9.0-rc'),
        createMockParsedAIM('amdenterpriseai/model-a', '1.5.0'),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].latestAim!.imageVersion).toBe('1.5.0');
    });

    it('sets isSupported to true when at least one version is Ready', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0', {
          status: AIMStatus.READY,
        }),
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0', {
          status: AIMStatus.NOT_AVAILABLE,
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].isSupported).toBe(true);
    });

    it('latestAim is latest official READY version, null when no official READY exists', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0', {
          status: AIMStatus.NOT_AVAILABLE,
        }),
        createMockParsedAIM('amdenterpriseai/model-a', '1.5.0', {
          status: AIMStatus.READY,
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].latestAim?.imageVersion).toBe('1.5.0');
    });

    it('sets isSupported to false and latestAim to null when no version is Ready', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/model-a', '2.0.0', {
          status: AIMStatus.NOT_AVAILABLE,
        }),
        createMockParsedAIM('amdenterpriseai/model-a', '1.0.0', {
          status: AIMStatus.NOT_AVAILABLE,
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].isSupported).toBe(false);
      expect(result[0].latestAim).toBeNull();
    });

    it('sorts supported models before unsupported models', () => {
      const aims = [
        createMockParsedAIM('amdenterpriseai/unsupported', '1.0.0', {
          status: AIMStatus.NOT_AVAILABLE,
        }),
        createMockParsedAIM('amdenterpriseai/supported', '1.0.0', {
          status: AIMStatus.READY,
        }),
      ];

      const result = transformToAggregatedAIMs(aims);

      expect(result[0].repository).toBe('amdenterpriseai/supported');
      expect(result[0].isSupported).toBe(true);
      expect(result[1].repository).toBe('amdenterpriseai/unsupported');
      expect(result[1].isSupported).toBe(false);
    });
  });

  describe('deployAim', () => {
    it('sends payload as-is (camelCase) to the API', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: 'new-service-id' }),
      });
      vi.stubGlobal('fetch', mockFetch);

      const payload: AIMDeployPayload = {
        model: 'llama3-8b',
        hfToken: 'my-hf-secret',
        imagePullSecrets: ['s1'],
        allowUnoptimized: true,
        minReplicas: 2,
        maxReplicas: 10,
        autoScaling: {
          metrics: [
            {
              type: 'PodMetric',
              podmetric: {
                metric: {
                  backend: 'opentelemetry',
                  metricNames: ['vllm:num_requests_waiting'],
                  query: 'vllm:num_requests_waiting',
                  operationOverTime: 'avg',
                },
                target: { type: 'Value', value: '5' },
              },
            },
          ],
        },
      };

      await deployAim('test-ns', payload);

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toEqual(payload);
      expect(body.hfToken).toBe('my-hf-secret');
      expect(body.imagePullSecrets).toEqual(['s1']);
      expect(body.allowUnoptimized).toBe(true);
      expect(body.minReplicas).toBe(2);
      expect(body.maxReplicas).toBe(10);
      expect(body.autoScaling).toEqual(payload.autoScaling);

      vi.unstubAllGlobals();
    });
  });
});
