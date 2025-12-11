// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ChatContext } from '@/types/chat';
import { Workload } from '@/types/workloads';
import { Aim } from '@/types/aims';
import { Model } from '@/types/models';

export const printContextToConsole = async (
  debugMode: boolean,
  context: ChatContext | undefined,
) => {
  if (debugMode && !!context?.messages?.length) {
    const userMessage = context.messages
      .slice()
      .reverse()
      .find((m) => m.role === 'user');
    console.log(userMessage ? userMessage.content : 'No user message');
  }
};

export const getCanonicalNameFromWorkload = (
  workload: Workload,
  aims: Aim[],
  models: Model[],
): string | undefined => {
  // Check if workload has an associated AIM
  if (workload.aimId) {
    const aim = aims.find((a) => a.workload?.id === workload.id);
    if (aim?.canonicalName) {
      return aim.canonicalName;
    }
  }

  // Check if workload has an associated Model
  if (workload.modelId) {
    const model = models.find((m) => m.id === workload.modelId);
    if (model?.canonicalName) {
      return model.canonicalName;
    }
  }

  return undefined;
};
