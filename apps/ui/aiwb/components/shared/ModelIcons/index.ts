// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  DeepseekIcon,
  DefaultIcon,
  GemmaIcon,
  MistralIcon,
  MixtralIcon,
  QwenIcon,
  CoherelabsIcon,
  OpenAIIcon,
} from '@/assets/svg/model-icons';

export const ModelIcons = {
  default: DefaultIcon,
  deepseek: DeepseekIcon,
  gemma: GemmaIcon,
  mistral: MistralIcon,
  mixtral: MixtralIcon,
  qwen: QwenIcon,
  coherelabs: CoherelabsIcon,
  openai: OpenAIIcon,
} as const;

export type ModelIconType = keyof typeof ModelIcons;

export {
  DefaultIcon,
  DeepseekIcon,
  GemmaIcon,
  MistralIcon,
  MixtralIcon,
  QwenIcon,
  CoherelabsIcon,
  OpenAIIcon,
};

export { ModelIcon } from './ModelIcon';
