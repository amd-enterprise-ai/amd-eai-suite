// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { aimParser, aimsParser } from '@/utils/app/aims';
import { AimWorkloadStatus } from '@/types/aims';
import { WorkloadStatus } from '@/types/enums/workloads';

describe('aims utils', () => {
  describe('aimParser', () => {
    it('parses aim labels correctly', () => {
      const aim: any = {
        imageTag: '1.0.0',
        labels: {
          'org.opencontainers.image.title': 'Test AIM',
          'org.opencontainers.image.description.short': 'Short description',
          'com.amd.aim.description.full': 'Full description',
          'org.opencontainers.image.version': 'v1.0',
          'com.amd.aim.model.tags': 'tag1, tag2, tag3',
          'com.amd.aim.model.canonicalName': 'test/model',
        },
      };

      const result = aimParser(aim);

      expect(result.title).toBe('Test AIM');
      expect(result.description.short).toBe('Short description');
      expect(result.description.full).toBe('Full description');
      expect(result.imageVersion).toBe('v1.0');
      expect(result.tags).toEqual(['tag1', 'tag2', 'tag3']);
      expect(result.canonicalName).toBe('test/model');
      expect(result.isPreview).toBe(false);
      expect(result.isHfTokenRequired).toBe(false);
    });

    it('detects preview versions correctly', () => {
      const aimDev: any = { imageTag: '1.0.0-dev', labels: {} };
      const aimRc: any = { imageTag: '1.0.0-rc', labels: {} };
      const aimPreview: any = { imageTag: '1.0.0-preview', labels: {} };
      const aimStable: any = { imageTag: '1.0.0', labels: {} };

      expect(aimParser(aimDev).isPreview).toBe(true);
      expect(aimParser(aimRc).isPreview).toBe(true);
      expect(aimParser(aimPreview).isPreview).toBe(true);
      expect(aimParser(aimStable).isPreview).toBe(false);
    });

    it('determines workload status correctly', () => {
      const aimDeployed: any = {
        imageTag: '1.0.0',
        labels: {},
        workload: { status: WorkloadStatus.RUNNING },
      };
      const aimPending: any = {
        imageTag: '1.0.0',
        labels: {},
        workload: { status: WorkloadStatus.PENDING },
      };
      const aimNotDeployed: any = {
        imageTag: '1.0.0',
        labels: {},
      };

      expect(aimParser(aimDeployed).workloadStatus).toBe(
        AimWorkloadStatus.DEPLOYED,
      );
      expect(aimParser(aimPending).workloadStatus).toBe(
        AimWorkloadStatus.PENDING,
      );
      expect(aimParser(aimNotDeployed).workloadStatus).toBe(
        AimWorkloadStatus.NOT_DEPLOYED,
      );
    });

    it('parses hfToken.required correctly', () => {
      const aimWithTokenRequired: any = {
        imageTag: '1.0.0',
        labels: {
          'com.amd.aim.hfToken.required': 'true',
        },
      };
      const aimWithTokenNotRequired: any = {
        imageTag: '1.0.0',
        labels: {
          'com.amd.aim.hfToken.required': 'false',
        },
      };
      const aimWithTokenRequiredCaseInsensitive: any = {
        imageTag: '1.0.0',
        labels: {
          'com.amd.aim.hfToken.required': 'TRUE',
        },
      };
      const aimWithoutTokenLabel: any = {
        imageTag: '1.0.0',
        labels: {},
      };

      expect(aimParser(aimWithTokenRequired).isHfTokenRequired).toBe(true);
      expect(aimParser(aimWithTokenNotRequired).isHfTokenRequired).toBe(false);
      expect(
        aimParser(aimWithTokenRequiredCaseInsensitive).isHfTokenRequired,
      ).toBe(true);
      expect(aimParser(aimWithoutTokenLabel).isHfTokenRequired).toBe(false);
    });

    it('parses recommendedDeployments correctly', () => {
      const aimWithRecommendedDeployments: any = {
        imageTag: '1.0.0',
        labels: {},
        recommendedDeployments: [
          {
            gpuModel: 'MI300X',
            gpuCount: 1,
            precision: 'fp8',
            metric: 'latency',
            description: 'Optimized for latency',
          },
          {
            gpuModel: 'MI300X',
            gpuCount: 1,
            precision: 'fp8',
            metric: 'throughput',
            description: 'Optimized for throughput',
          },
        ],
      };

      const result = aimParser(aimWithRecommendedDeployments);
      expect(result.recommendedDeployments).toHaveLength(2);
      expect(result.recommendedDeployments[0].metric).toBe('latency');
      expect(result.recommendedDeployments[1].metric).toBe('throughput');
      expect(result.availableMetrics).toEqual(['latency', 'throughput']);
    });

    it('parses single recommendedDeployment correctly', () => {
      const aimWithSingleDeployment: any = {
        imageTag: '1.0.0',
        labels: {},
        recommendedDeployments: [
          {
            gpuModel: 'MI300X',
            gpuCount: 1,
            precision: 'fp8',
            metric: 'latency',
            description: 'Optimized for latency',
          },
        ],
      };

      const result = aimParser(aimWithSingleDeployment);
      expect(result.recommendedDeployments).toHaveLength(1);
      expect(result.recommendedDeployments[0].metric).toBe('latency');
      expect(result.availableMetrics).toEqual(['latency']);
    });

    it('handles missing recommendedDeployments from API gracefully', () => {
      const aimWithoutDeploymentsFromAPI: any = {
        imageTag: '1.0.0',
        labels: {},
        // recommendedDeployments not provided by API
      };

      const result = aimParser(aimWithoutDeploymentsFromAPI);
      expect(result.recommendedDeployments).toEqual([]);
      expect(result.availableMetrics).toEqual([]);
    });

    it('extracts unique metrics from recommendedDeployments', () => {
      const aimWithDuplicateMetrics: any = {
        imageTag: '1.0.0',
        labels: {},
        recommendedDeployments: [
          {
            gpuModel: 'MI300X',
            gpuCount: 1,
            precision: 'fp8',
            metric: 'latency',
            description: 'Config 1',
          },
          {
            gpuModel: 'MI300X',
            gpuCount: 8,
            precision: 'fp16',
            metric: 'latency',
            description: 'Config 2',
          },
          {
            gpuModel: 'MI300X',
            gpuCount: 1,
            precision: 'fp8',
            metric: 'throughput',
            description: 'Config 3',
          },
        ],
      };

      const result = aimParser(aimWithDuplicateMetrics);
      expect(result.recommendedDeployments).toHaveLength(3);
      expect(result.availableMetrics).toEqual(['latency', 'throughput']);
    });
  });

  describe('aimsParser', () => {
    it('parses array of aims and filters empty titles', () => {
      const aims: any[] = [
        {
          imageTag: '1.0.0',
          labels: {
            'org.opencontainers.image.title': 'AIM 1',
          },
        },
        {
          imageTag: '1.0.0',
          labels: {},
        },
        {
          imageTag: '1.0.0',
          labels: {
            'org.opencontainers.image.title': 'AIM 2',
          },
        },
      ];

      const result = aimsParser(aims);

      expect(result).toHaveLength(2);
      expect(result[0].title).toBe('AIM 1');
      expect(result[1].title).toBe('AIM 2');
    });
  });
});
