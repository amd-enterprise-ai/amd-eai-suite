// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { aimParser } from '@/lib/app/aims';
import {
  AIMWorkloadStatus,
  AIMServiceStatus,
  AIMClusterModel,
  AIMService,
} from '@/types/aims';

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
        title: 'Test AIM',
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
        comAmdAimTitle: 'Test AIM',
        orgOpencontainersImageAuthors: 'Test Author',
        orgOpencontainersImageCreated: '2023-01-01T00:00:00Z',
        orgOpencontainersImageDescription: 'Short description',
        orgOpencontainersImageDocumentation: 'https://docs.example.com',
        orgOpencontainersImageLicenses: 'MIT',
        orgOpencontainersImageRefName: '1.0.0',
        orgOpencontainersImageRevision: 'abc123',
        orgOpencontainersImageSource: 'https://github.com/example/model',
        orgOpencontainersImageTitle: 'Test AIM',
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
    model: { name: 'test-aim' },
    replicas: 1,
    overrides: {},
    cacheModel: true,
    routing: { annotations: {}, enabled: true },
    runtimeConfigName: 'default',
    template: {},
  },
  status: { status },
  resourceName: 'test-service',
  clusterAuthGroupId: null,
  endpoints: {
    internal: 'http://test-service.test-namespace.svc.cluster.local',
    external: 'https://api.example.com/test-namespace/service-123',
  },
});

describe('aims utils', () => {
  describe('aimParser', () => {
    it('parses aim fields correctly', () => {
      const aim = createMockAIM();
      const result = aimParser(aim);

      expect(result.title).toBe('Test AIM');
      expect(result.description.short).toBe('Short description');
      expect(result.description.full).toBe('Full description');
      expect(result.canonicalName).toBe('test/model');
      expect(result.isPreview).toBe(false);
      expect(result.isHfTokenRequired).toBe(false);
    });

    it('detects preview versions via tags', () => {
      const aim = createMockAIM({
        status: {
          status: 'Ready' as any,
          imageMetadata: {
            model: {
              canonicalName: 'test/model',
              hfTokenRequired: false,
              source: 'https://example.com',
              tags: ['test', 'preview'],
              title: 'Test AIM',
              variants: [],
            },
            originalLabels: {} as any,
          },
        },
      });

      expect(aimParser(aim).isPreview).toBe(true);
    });

    it('non-preview tags do not mark as preview', () => {
      const aim = createMockAIM();
      expect(aimParser(aim).isPreview).toBe(false);
    });

    it('determines workload status from deployed services', () => {
      const aim = createMockAIM();

      expect(aimParser(aim).workloadStatuses).toEqual([
        AIMWorkloadStatus.NOT_DEPLOYED,
      ]);
      expect(
        aimParser(aim, [createMockService(AIMServiceStatus.RUNNING)])
          .workloadStatuses,
      ).toContain(AIMWorkloadStatus.DEPLOYED);
      expect(
        aimParser(aim, [createMockService(AIMServiceStatus.PENDING)])
          .workloadStatuses,
      ).toContain(AIMWorkloadStatus.PENDING);
      expect(
        aimParser(aim, [createMockService(AIMServiceStatus.FAILED)])
          .workloadStatuses,
      ).toContain(AIMWorkloadStatus.FAILED);
      expect(
        aimParser(aim, [createMockService(AIMServiceStatus.DEGRADED)])
          .workloadStatuses,
      ).toContain(AIMWorkloadStatus.DEGRADED);
    });

    it('parses hfTokenRequired correctly', () => {
      const aimRequired = createMockAIM({
        status: {
          status: 'Ready' as any,
          imageMetadata: {
            model: {
              canonicalName: 'test/model',
              hfTokenRequired: true,
              source: 'https://example.com',
              tags: [],
              title: 'Test AIM',
              variants: [],
            },
            originalLabels: {} as any,
          },
        },
      });
      const aimNotRequired = createMockAIM();

      expect(aimParser(aimRequired).isHfTokenRequired).toBe(true);
      expect(aimParser(aimNotRequired).isHfTokenRequired).toBe(false);
    });

    it('handles empty deployedServices array', () => {
      const aim = createMockAIM();
      const result = aimParser(aim, []);

      expect(result.workloadStatuses).toEqual([AIMWorkloadStatus.NOT_DEPLOYED]);
      expect(result.deployedServices).toEqual([]);
    });

    it('handles multiple deployed services', () => {
      const aim = createMockAIM();
      const services = [
        createMockService(AIMServiceStatus.RUNNING),
        createMockService(AIMServiceStatus.PENDING),
      ];
      const result = aimParser(aim, services);

      expect(result.workloadStatuses).toEqual([
        AIMWorkloadStatus.DEPLOYED,
        AIMWorkloadStatus.PENDING,
      ]);
      expect(result.deployedServices).toEqual(services);
    });
  });
});
