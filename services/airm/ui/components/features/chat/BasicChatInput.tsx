// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconRepeat } from '@tabler/icons-react';
import {
  Dispatch,
  KeyboardEvent,
  MutableRefObject,
  SetStateAction,
  useEffect,
  useState,
} from 'react';

import { useTranslation } from 'next-i18next';

import { isMobile } from '@/utils/app/browser';

import { Message } from '@/types/chat';

import { ChatTextArea } from './ChatTextArea';

interface Props {
  content: string;
  setContent: Dispatch<SetStateAction<string>>;
  onSend: (message: Message) => void;
  onRegenerate?: () => void;
  onScrollDownClick: () => void;
  stopConversationRef: MutableRefObject<boolean>;
  textareaRef: MutableRefObject<HTMLTextAreaElement | null>;
  showScrollDownButton: boolean;
  allowRegenerate: boolean;
  disabled: boolean;
  messageIsStreaming: boolean;
}

export const BasicChatInput = ({
  content,
  setContent,
  onSend,
  onRegenerate,
  onScrollDownClick,
  stopConversationRef,
  textareaRef,
  showScrollDownButton,
  allowRegenerate,
  disabled,
  messageIsStreaming,
}: Props) => {
  const { t } = useTranslation('chat');

  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [sendDisabled, setSendDisabled] = useState(true);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setSendDisabled(value.trim().length === 0);

    setContent(value);
  };

  const handleSend = () => {
    if (messageIsStreaming) {
      return;
    }

    if (!content) {
      return;
    }

    try {
      onSend({ role: 'user', content });
      setContent('');
      setSendDisabled(true);

      if (window.innerWidth < 640 && textareaRef?.current) {
        textareaRef.current.blur();
      }
    } catch (error) {
      console.error('Error sending message: ', error);
    }
  };

  const handleStopConversation = () => {
    stopConversationRef.current = true;
    setTimeout(() => {
      stopConversationRef.current = false;
    }, 1000);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !isTyping && !isMobile() && !e.shiftKey) {
      e.preventDefault();

      if (!sendDisabled) {
        handleSend();
      }
    }
  };

  useEffect(() => {
    if (textareaRef?.current) {
      textareaRef.current.style.height = 'inherit';
      textareaRef.current.style.height = `${textareaRef.current?.scrollHeight}px`;
      textareaRef.current.style.overflow = `${
        textareaRef?.current?.scrollHeight > 400 ? 'auto' : 'hidden'
      }`;
    }

    if (content.length > 0) {
      setSendDisabled(false);
    }
  }, [content, textareaRef]);

  return (
    <div className="absolute bottom-0 left-0 right-0 flex justify-center py-6 md:py-12 bg-gradient-to-b from-transparent via-default-50 to-default-50 z-10">
      <div className="flex justify-center mx-2 md:mx-8 w-full md:w-2/3 lg:w-1/2 max-w-[500px]">
        <ChatTextArea
          content={content}
          handleChange={handleChange}
          handleKeyDown={handleKeyDown}
          setIsTyping={setIsTyping}
          textareaRef={textareaRef}
          disabled={disabled}
          messageIsStreaming={messageIsStreaming}
          sendDisabled={sendDisabled}
          handleSend={handleSend}
          handleStopConversation={handleStopConversation}
          showScrollDownButton={showScrollDownButton}
          onScrollDownClick={onScrollDownClick}
        />

        {allowRegenerate && !messageIsStreaming && (
          <button
            className="absolute -top-4 shadow-lg left-0 right-0 mx-auto mb-3 flex w-fit items-center gap-3 rounded-lg bg-primary py-2 px-4 text-white md:mb-0 md:mt-2"
            onClick={onRegenerate}
          >
            <IconRepeat size={16} /> {t('chatInput.regenerateResponse')}
          </button>
        )}
      </div>
    </div>
  );
};
