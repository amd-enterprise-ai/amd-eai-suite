// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ParsedAIM } from '@/types/aims';
import { ChattableResponse, ChatWorkloadType } from '@/types/chat';
import { WorkloadType } from '@amdenterpriseai/types';
import { AIMServiceStatus } from '@/types/aims';
import { WorkloadStatus } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';
import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';
import {
  fetchProfilesForServices,
  getAimClusterModels,
  getAimServices,
  resolveAIMServiceDisplay,
} from './aims';

const convertAIMServiceStatus = (aimServiceStatus: AIMServiceStatus) => {
  if (aimServiceStatus === AIMServiceStatus.RUNNING) {
    return WorkloadStatus.RUNNING;
  } else if (
    aimServiceStatus === AIMServiceStatus.PENDING ||
    aimServiceStatus === AIMServiceStatus.STARTING
  ) {
    return WorkloadStatus.PENDING;
  } else if (aimServiceStatus === AIMServiceStatus.DEGRADED) {
    return WorkloadStatus.DEGRADED;
  } else if (aimServiceStatus === AIMServiceStatus.FAILED) {
    return WorkloadStatus.FAILED;
  }
  return WorkloadStatus.UNKNOWN;
};

export type WorkloadDisplayInfo = {
  imageVersion: string;
  metric: string;
  gpu?: string | null;
  templateGpuCount?: number | null;
  precision?: string | null;
};

export type ChattableWorkloadsResult = {
  workloads: Workload[];
  workloadDisplayInfo: Record<string, WorkloadDisplayInfo>;
};

export const listChattableWorkloads = async (
  projectId: string,
): Promise<ChattableWorkloadsResult> => {
  if (!projectId) {
    throw new APIRequestError(`No project selected`, 422);
  }

  const [chattableRes, aimServices] = await Promise.all([
    fetch(`/api/namespaces/${projectId}/chattable`, { method: 'GET' }),
    getAimServices(projectId).catch(() => []),
  ]);

  if (!chattableRes.ok) {
    const errorMessage = await getErrorMessage(chattableRes);
    throw new APIRequestError(
      `Failed to list chattable workloads: ${errorMessage}`,
      chattableRes.status,
    );
  }

  const chattableList = (await chattableRes.json()) as ChattableResponse;

  const profileByServiceId = await fetchProfilesForServices(aimServices);

  // Fetch ParsedAIMs to resolve display names (canonical names)
  let parsedAIMs: ParsedAIM[] | undefined;
  try {
    parsedAIMs = await getAimClusterModels(projectId);
  } catch (error) {
    console.warn(
      'Failed to fetch AIM cluster models for display names:',
      error,
    );
  }

  const workloadDisplayInfo: Record<string, WorkloadDisplayInfo> = {};
  const chattableWorkloads = [
    ...chattableList.aimServices.map((s) => {
      const displayInfo = resolveAIMServiceDisplay(s, parsedAIMs);
      const modelRef = s.status.resolvedModel?.name;
      const displayName =
        displayInfo.canonicalName ||
        displayInfo.title ||
        modelRef ||
        s.metadata.name;
      workloadDisplayInfo[s.id as string] = {
        imageVersion: displayInfo.imageVersion,
        metric: displayInfo.metric,
      };
      return {
        id: s.id as string,
        aimId: modelRef,
        type: WorkloadType.INFERENCE,
        tags: displayInfo.tags,
        name: modelRef || s.metadata.name,
        displayName,
        createdBy: '',
        createdAt: s.metadata.creationTimestamp,
        updatedAt: s.metadata.creationTimestamp,
        status: convertAIMServiceStatus(s.status.status),
        output: {
          internalHost: s.endpoints.internal,
          externalHost: s.endpoints.external,
        },
      };
    }),
    ...chattableList.workloads,
  ];

  for (const s of chattableList.aimServices) {
    const id = s.id as string;
    const existing = workloadDisplayInfo[id];
    if (!existing) continue;
    const profile = profileByServiceId.get(id);
    if (!profile) continue;
    workloadDisplayInfo[id] = {
      ...existing,
      ...(profile.metric != null && profile.metric !== ''
        ? { metric: profile.metric }
        : {}),
      ...(profile.gpu != null && profile.gpu !== ''
        ? { gpu: profile.gpu }
        : {}),
      ...(profile.templateGpuCount != null
        ? { templateGpuCount: profile.templateGpuCount }
        : {}),
      ...(profile.precision != null && profile.precision !== ''
        ? { precision: profile.precision }
        : {}),
    };
  }

  return {
    workloads: chattableWorkloads,
    workloadDisplayInfo,
  };
};

import { ChatBody } from '@/types/chat';
import { INFERENCE_CHUNK_DELIMITER, InferenceChunk } from '@/types/chat';
import { MutableRefObject } from 'react';
import { useSystemToast } from '@amdenterpriseai/hooks';

export const streamChatResponse = async (
  workloadId: string,
  workloadType: ChatWorkloadType,
  chatBody: ChatBody,
  projectId: string,
  stopConversationRef: MutableRefObject<boolean>,
) => {
  const { toast } = useSystemToast();

  const chatController = new AbortController();
  const data = await sendChatRequest(
    workloadId,
    workloadType,
    chatBody,
    projectId,
    chatController,
  );

  if (!data) {
    toast.error('No response received');
    throw new Error('No response received from chat request');
  }
  const decoder = new TextDecoder();

  let resolveContextPromise: (arg: any) => void;
  const chatContextPromise = new Promise<any>((resolve, _reject) => {
    resolveContextPromise = resolve;
  });

  let context = {};
  const responseStream = new ReadableStream({
    async start(controller) {
      let done = false;
      const reader = data.getReader();
      let currentChunk = '';
      while (!done) {
        if (stopConversationRef.current === true) {
          chatController.abort();
          done = true;
          break;
        }
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const decoded = decoder.decode(value);
          const chunks = decoded
            .split(INFERENCE_CHUNK_DELIMITER)
            .filter((c) => c !== '');
          for (const chunk of chunks) {
            let chunkValue: InferenceChunk;
            currentChunk += chunk;
            try {
              chunkValue = JSON.parse(currentChunk) as InferenceChunk;
            } catch (error) {
              continue;
            }
            currentChunk = '';

            if (chunkValue.content) {
              controller.enqueue(chunkValue.content);
            }
            if (chunkValue.context) {
              context = { ...context, ...chunkValue.context };
            }
          }
        }
      }
      controller.close();
      resolveContextPromise(Object.keys(context).length ? context : undefined);
    },
  });

  return {
    responseStream,
    context: chatContextPromise,
  };
};

export const sendChatRequest = async (
  workloadId: string,
  workloadType: ChatWorkloadType,
  chatBody: ChatBody,
  projectId: string,
  chatController: AbortController,
) => {
  const body = JSON.stringify(chatBody);

  const servicePath =
    workloadType === ChatWorkloadType.AIMService
      ? `aims/services/${workloadId}/chat`
      : `workloads/${workloadId}/chat`;

  const response = await fetch(`/api/namespaces/${projectId}/${servicePath}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    signal: chatController.signal,
    body,
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to send chat request: ${errorMessage}`,
      response.status,
    );
  }
  return response.body;
};
