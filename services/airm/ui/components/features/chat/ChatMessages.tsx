// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { RefObject, memo } from 'react';

import { ChatConversation } from '@/types/chat';

import { ChatLoader } from './ChatLoader';
import { MemoizedChatMessage } from './MemoizedChatMessage';

interface Props {
  conversation: ChatConversation;
  compareMode: boolean;
  messagesEndRef: RefObject<HTMLDivElement | null>;
  onConversationUpdated: (conversation: ChatConversation) => void;
  loading: boolean;
  messageIsStreaming: boolean;
}

export const ChatMessages = memo(
  ({
    conversation,
    messagesEndRef,
    compareMode,
    loading,
    messageIsStreaming,
  }: Props) => {
    return (
      <div className="flex flex-col w-full" data-testid="chat-messages">
        <div className="relative">
          <div
            className={
              'flex w-full ' + (!compareMode ? 'xl:justify-center' : '')
            }
          >
            <div
              className={
                'px-2 md:px-8 lg:px-10 max-w-[100%] ' +
                (!compareMode ? 'xl:w-[768px]' : '')
              }
            >
              {conversation.messages.map((message, index, filteredMessages) => (
                <MemoizedChatMessage
                  key={index}
                  message={message}
                  showCursorOnMessage={index === filteredMessages.length - 1}
                  allowEdit={false}
                  allowCopy={true}
                  debugInfo={message.debugInfo}
                  messageIsStreaming={messageIsStreaming}
                />
              ))}
              {conversation.messages && loading && <ChatLoader />}
              <div className="h-[172px]" ref={messagesEndRef} />
            </div>
          </div>
        </div>
      </div>
    );
  },
);
ChatMessages.displayName = 'ChatMessages';
