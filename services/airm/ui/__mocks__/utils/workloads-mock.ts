// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ProjectStatus } from '@/types/enums/projects';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

import { v4 as uuidv4 } from 'uuid';

export const generateMockWorkspaceWorkloads = (
  n: number,
  name: string,
  status: WorkloadStatus,
  type: WorkloadType,
): Workload[] => {
  const template = {
    id: '',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    createdBy: 'user@amd.com',
    updatedBy: 'system',
    displayName: '',
    name: '',
    project: {
      id: '',
      name: 'demo-project',
      description: 'Demo project',
      status: ProjectStatus.READY,
      statusReason: null,
      clusterId: '',
    },
    projectId: '',
    status,
    type,
    chartId: '',
    modelId: null,
    datasetId: null,
    userInputs: {
      gpus: 1,
      image: '',
      kaiwo: { enabled: true },
      ingress: { enabled: true },
      metadata: {
        userId: '',
        projectId: '',
        annotations: {
          pvcSilogenAiUserPvcUid: '',
          pvcSilogenAiUserPvcSize: '60Gi',
          pvcSilogenAiUserPvcAutoCreate: 'true',
          pvcSilogenAiUserPvcStorageClassName: 'multinode',
        },
        workloadId: '',
      },
      httpRoute: { enabled: true },
      cpuPerGpu: 4,
      memoryPerGpu: 128,
      imagePullSecrets: [],
      persistentStorage: {
        enabled: true,
        volumes: {
          pvcUser: {
            pvcName: '',
            mountPath: '',
          },
        },
      },
    },
    output: {
      externalHost: '',
      internalHost: '',
    },
    allocatedResources: {
      gpuCount: null,
      vram: null,
    },
    capabilities: [],
    manifest: null,
  };

  return Array.from({ length: n }, () => {
    const workloadId = uuidv4();
    const clusterId = uuidv4();
    const chartId = uuidv4();
    const projectId = uuidv4();
    const userId = uuidv4();

    return {
      ...template,
      id: workloadId,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      displayName: `${name}-${new Date()
        .toISOString()
        .replace(/[-:.TZ]/g, '')
        .slice(0, 14)}`,
      name: `mw-dev-tracking-${name}-${Math.floor(Math.random() * 1000000000)}-${workloadId.slice(0, 4)}`,
      project: {
        ...template.project,
        id: projectId,
        clusterId,
      },
      projectId,
      status,
      chartId,
      type,
      userInputs: {
        ...template.userInputs,
        image: `ghcr.io/${name}/${name}:v2.22.0`,
        metadata: {
          ...template.userInputs.metadata,
          userId,
          projectId,
          annotations: {
            ...template.userInputs.metadata.annotations,
            pvcSilogenAiUserPvcUid: `${name}-{{ .Values.metadata.project_id }}`,
          },
          workloadId,
        },
        persistentStorage: {
          ...template.userInputs.persistentStorage,
          volumes: {
            pvcUser: {
              pvcName: `pvc-${name}-{{ .Values.metadata.project_id }}`,
              mountPath: `/workload/{{ .Values.metadata.project_id }}`,
            },
          },
        },
      },
      output: {
        externalHost: `https://workloads.staging.silogen.ai/${projectId}/${userId}/${workloadId}/`,
        internalHost: `mw-dev-tracking-${name}-${Math.floor(Math.random() * 1000000000)}-${workloadId.slice(0, 4)}.demo.svc.cluster.local/`,
      },
    };
  });
};
