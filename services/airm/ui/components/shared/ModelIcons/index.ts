// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import DeepseekIcon from '@/assets/svg/model-icons/deepseek.svg';
import DefaultIcon from '@/assets/svg/model-icons/default.svg';
import GemmaIcon from '@/assets/svg/model-icons/gemma.svg';
import MistralIcon from '@/assets/svg/model-icons/mistral.svg';
import MixtralIcon from '@/assets/svg/model-icons/mixtral.svg';
import QwenIcon from '@/assets/svg/model-icons/qwen.svg';

export const ModelIcons = {
  default: DefaultIcon,
  deepseek: DeepseekIcon,
  gemma: GemmaIcon,
  mistral: MistralIcon,
  mixtral: MixtralIcon,
  qwen: QwenIcon,
} as const;

export type ModelIconType = keyof typeof ModelIcons;

export {
  DefaultIcon,
  DeepseekIcon,
  GemmaIcon,
  MistralIcon,
  MixtralIcon,
  QwenIcon,
};

export { ModelIcon } from './ModelIcon';
