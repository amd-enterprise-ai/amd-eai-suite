// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { FC, memo } from 'react';

import { ChatMessage, Props } from './ChatMessage';

export const MemoizedChatMessage: FC<Props> = memo(
  ChatMessage,
  (prevProps, nextProps) =>
    prevProps.showCursorOnMessage == nextProps.showCursorOnMessage &&
    prevProps.message.content === nextProps.message.content &&
    prevProps.debugInfo === nextProps.debugInfo,
);
