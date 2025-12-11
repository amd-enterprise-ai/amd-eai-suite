// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button, Tab, Tabs } from '@heroui/react';
import { IconEraser, IconSettings } from '@tabler/icons-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useTranslation } from 'next-i18next';
import { useSearchParams } from 'next/navigation';
import router from 'next/router';

import { useChatWindowScroll } from '@/hooks/useChatWindowScroll';
import useSystemToast from '@/hooks/useSystemToast';

import { streamChatResponse } from '@/services/app/chat';
import { getAims } from '@/services/app/aims';
import { getModels } from '@/services/app/models';

import { getCanonicalNameFromWorkload } from '@/utils/app/chat';
import { getChatSettings, saveChatSettings } from '@/utils/app/chat-settings';

import {
  ChatBody,
  ChatContext,
  ChatConversation,
  DebugInfo,
  Message,
} from '@/types/chat';
import { DEFAULT_SETTINGS, InferenceSettings, Model } from '@/types/models';
import { Workload } from '@/types/workloads';
import { Aim } from '@/types/aims';

import { BasicChatInput } from '@/components/features/chat/BasicChatInput';
import { Toolbar } from '@/components/layouts/ToolbarLayout';
import ModelDeploymentSelect from '@/components/shared/Select/ModelDeploymentSelect';

import ChatInfoCard from './ChatInfoCard';
import { ChatMessages } from './ChatMessages';
import SettingsDrawer from './SettingsDrawer';
import { useProject } from '@/contexts/ProjectContext';
import { DELAYED_RESPONSE_THRESHOLD_MS } from './constants';

interface ChatViewProps {
  workloads: Workload[];
}

export const ChatView = ({ workloads }: ChatViewProps) => {
  const { toast } = useSystemToast();
  const { t } = useTranslation('chat');
  const { activeProject } = useProject();
  const searchParams = useSearchParams();
  const workloadParam = searchParams?.get('workload');

  // Use cached aims and models data from React Query
  const { data: aims = [] } = useQuery<Aim[]>({
    queryKey: ['project', activeProject, 'aim-catalog'],
    queryFn: () => getAims(activeProject!),
    enabled: !!activeProject,
  });

  const { data: models = [] } = useQuery<Model[]>({
    queryKey: ['project', activeProject, 'custom-models'],
    queryFn: () => getModels(activeProject!),
    enabled: !!activeProject,
  });

  const [firstLoading, setFirstLoading] = useState<boolean>(false);
  const firstDelayedResponseTimer = useRef<
    string | number | NodeJS.Timeout | undefined
  >(undefined);
  const [
    firstDelayedResponseNotification,
    setFirstDelayedResponseNotification,
  ] = useState<boolean>(false);
  const [firstMessageIsStreaming, setFirstMessageIsStreaming] =
    useState<boolean>(false);

  const [secondLoading, setSecondLoading] = useState<boolean>(false);
  const secondDelayedResponseTimer = useRef<
    string | number | NodeJS.Timeout | undefined
  >(undefined);
  const [
    secondDelayedResponseNotification,
    setSecondDelayedResponseNotification,
  ] = useState<boolean>(false);
  const [secondMessageIsStreaming, setSecondMessageIsStreaming] =
    useState<boolean>(false);

  const [chatMode, setChatMode] = useState<'chat' | 'compare'>('chat');

  const [firstConversation, setFirstConversation] = useState<ChatConversation>({
    messages: [],
    streaming: false,
  });
  const [firstModelWorkload, setFirstModelWorkload] = useState<
    Workload | undefined
  >(workloads.length > 0 ? workloads[0] : undefined);
  const [firstSettings, setFirstSettings] = useState<InferenceSettings>(
    getChatSettings() || DEFAULT_SETTINGS,
  );

  // Second model configurations
  const [secondConversation, setSecondConversation] =
    useState<ChatConversation>({
      ...firstConversation,
    });
  const [secondModelWorkload, setSecondModelWorkload] = useState<
    Workload | undefined
  >(firstModelWorkload);
  const [secondSettings, setSecondSettings] = useState<InferenceSettings>(
    getChatSettings() || DEFAULT_SETTINGS,
  );

  const [syncSettings, setSyncSettings] = useState<boolean>(false);

  const [firstSettingsDrawerOpen, setFirstSettingsDrawerOpen] =
    useState<boolean>(false);
  const [secondSettingsDrawerOpen, setSecondSettingsDrawerOpen] =
    useState<boolean>(false);

  const messagesEndRef1 = useRef<HTMLDivElement>(null);
  const messagesEndRef2 = useRef<HTMLDivElement>(null);
  const chatContainerRef1 = useRef<HTMLDivElement>(null);
  const chatContainerRef2 = useRef<HTMLDivElement>(null);
  const stopConversationRef = useRef<boolean>(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [chatInputContent, setChatInputContent] = useState<string>('');

  function constructMessagesToSendToLLM(
    conversationMessages: Message[],
    systemPrompt: Message | undefined,
  ): Message[] {
    // Add a system prompt if specified, and remove extra fields from past messages
    const messages = [...conversationMessages];
    if (systemPrompt) {
      messages.unshift(systemPrompt);
    }
    return messages.map(
      (message) =>
        ({
          content: message.content,
          role: message.role,
        }) as Message,
    );
  }

  const getChatBody = (
    settings: InferenceSettings,
    messages: Message[],
    workload: Workload,
  ): ChatBody => {
    // Prepare the system prompt message if settings.systemPrompt is not empty
    const systemPromptMessage = settings.systemPrompt
      ? ({ role: 'system', content: settings.systemPrompt } as Message)
      : undefined;

    const canonicalName = getCanonicalNameFromWorkload(workload, aims, models);

    const chatBody = {
      stream: true,
      stream_options: {
        include_usage: true,
      },
      temperature: settings.temperature,
      frequency_penalty: settings.frequencyPenalty,
      presence_penalty: settings.presencePenalty,
    };

    return {
      ...chatBody,
      model: canonicalName,
      messages: constructMessagesToSendToLLM(messages, systemPromptMessage),
    } as ChatBody;
  };

  const populateDebugInformationOnLastMessage = (
    context: ChatContext | undefined,
    conversation: ChatConversation,
    conversationSetter: (conversation: ChatConversation) => void,
    sentMessages: Message[],
  ): ChatConversation => {
    const debugInfo: DebugInfo = {
      messages: sentMessages,
      usage: context?.usage,
    };

    const updatedMessages = conversation.messages;
    const lastElement = updatedMessages.pop();
    updatedMessages.push({
      ...lastElement,
      debugInfo: debugInfo,
    } as Message);
    conversation = {
      ...conversation,
      messages: updatedMessages,
    };
    conversationSetter(conversation);

    return conversation;
  };

  const handleSend = useCallback(
    async (
      conversation: ChatConversation,
      chatBody: ChatBody,
      workloadId: string,
      conversationSetter: (conversation: ChatConversation) => void,
      conversationRef: 'first' | 'second',
    ) => {
      if (conversationRef === 'first') {
        setFirstDelayedResponseNotification(false);
        firstDelayedResponseTimer.current = setTimeout(() => {
          setFirstDelayedResponseNotification(true);
        }, DELAYED_RESPONSE_THRESHOLD_MS);
        setFirstLoading(true);
      } else {
        setSecondDelayedResponseNotification(false);
        secondDelayedResponseTimer.current = setTimeout(() => {
          setSecondDelayedResponseNotification(true);
        }, DELAYED_RESPONSE_THRESHOLD_MS);
        setSecondLoading(true);
      }
      conversation.streaming = true;
      conversationSetter(conversation);
      try {
        const { responseStream, context } = await streamChatResponse(
          workloadId,
          chatBody,
          activeProject || '',
          stopConversationRef,
        );

        if (conversationRef === 'first') {
          clearTimeout(firstDelayedResponseTimer.current);
          setFirstDelayedResponseNotification(false);
          setFirstLoading(false);
        } else {
          clearTimeout(secondDelayedResponseTimer.current);
          setSecondDelayedResponseNotification(false);
          setSecondLoading(false);
        }

        let text = '';
        let updatedMessages: Message[] = [...conversation.messages];
        updatedMessages.push({
          role: 'assistant',
          content: text,
        });

        const responseStreamReader = responseStream.getReader();
        while (true) {
          const { value, done } = await responseStreamReader.read();

          if (done) {
            conversation = {
              ...conversation,
              streaming: false,
            };
            if (conversationRef === 'first') {
              setFirstMessageIsStreaming(false);
            } else {
              setSecondMessageIsStreaming(false);
            }
            conversationSetter(conversation);
            break;
          }
          text += value;
          const lastElement = updatedMessages.pop();
          updatedMessages.push({
            ...lastElement,
            content: text,
          } as Message);

          conversation = {
            ...conversation,
            messages: updatedMessages,
          };
          conversationSetter(conversation);
        }

        conversation = populateDebugInformationOnLastMessage(
          await context,
          conversation,
          conversationSetter,
          chatBody.messages,
        );
      } catch (error) {
        console.error('Error streaming chat response: ', error);
        toast.error(t('errors.chatResponseFailed'));
        if (conversation.messages.at(-1)?.role === 'user') {
          conversation.messages.pop();
        }

        if (conversationRef === 'first') {
          setFirstMessageIsStreaming(false);
          setFirstLoading(false);
          clearTimeout(firstDelayedResponseTimer.current);
          setFirstDelayedResponseNotification(false);
        } else {
          setSecondMessageIsStreaming(false);
          setSecondLoading(false);
          clearTimeout(secondDelayedResponseTimer.current);
          setSecondDelayedResponseNotification(false);
        }
        conversationSetter({
          ...conversation,
          streaming: false,
        });
      }
    },
    [stopConversationRef, toast, t, activeProject],
  );

  const updateSettings = (
    settings: InferenceSettings,
    settingsSetter: (settings: InferenceSettings) => void,
  ) => {
    saveChatSettings(settings);
    if (chatMode === 'compare' && syncSettings) {
      setFirstSettings(settings);
      setSecondSettings(settings);
    } else {
      settingsSetter(settings);
    }
  };

  const onFirstModelWorkloadChange = useCallback(
    (workloadId: string) => {
      const workload = workloads.find((w) => w.id === workloadId);

      if (workload) {
        setFirstModelWorkload(workload);

        const url = new URL(window.location.href);
        url.searchParams.set('workload', workload.id);
        router.push(url.toString(), undefined, { shallow: true });
      }
    },
    [workloads],
  );

  useEffect(() => {
    if (workloadParam) {
      onFirstModelWorkloadChange(workloadParam);
    }
  }, [workloadParam, onFirstModelWorkloadChange, workloads]);

  const onSecondModelWorkloadChange = (workloadId: string) => {
    const workload = workloads.find((w) => w.id === workloadId);

    if (workload) {
      setSecondModelWorkload(workload);
    }
  };

  const onMessage = (message: Message) => {
    setFirstMessageIsStreaming(true);
    setFirstLoading(false);

    if (!firstModelWorkload) {
      return;
    }

    firstConversation.messages = [...firstConversation.messages, message];

    const firstChatBody = getChatBody(
      firstSettings,
      firstConversation.messages,
      firstModelWorkload,
    );

    handleSend(
      firstConversation,
      firstChatBody,
      firstModelWorkload.id,
      setFirstConversation,
      'first',
    );

    if (chatMode === 'compare' && secondModelWorkload) {
      setSecondMessageIsStreaming(true);
      setSecondLoading(false);

      secondConversation.messages = [...secondConversation.messages, message];

      const secondChatBody = getChatBody(
        secondSettings,
        secondConversation.messages,
        secondModelWorkload,
      );
      handleSend(
        secondConversation,
        secondChatBody,
        secondModelWorkload.id,
        setSecondConversation,
        'second',
      );
    }
  };

  const clearAll = () => {
    setFirstConversation({ ...firstConversation, messages: [] });
    setSecondConversation({ ...secondConversation, messages: [] });
  };

  const { showScrollDownButton, handleScroll, handleScrollDown } =
    useChatWindowScroll(
      [messagesEndRef1, messagesEndRef2],
      [chatContainerRef1, chatContainerRef2],
    );

  // Always scroll to bottom when messages change or streaming
  useEffect(() => {
    messagesEndRef1.current?.scrollIntoView({ behavior: 'smooth' });
    if (chatMode === 'compare') {
      messagesEndRef2.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [
    firstConversation.messages,
    secondConversation.messages,
    firstConversation.streaming,
    secondConversation.streaming,
    chatMode,
  ]);

  return (
    <div className="relative flex flex-col w-full h-full">
      <Toolbar>
        <Tabs
          selectedKey={chatMode}
          onSelectionChange={(key) => setChatMode(key as 'chat' | 'compare')}
          aria-label="chat-mode-tabs"
          size="md"
        >
          <Tab key="chat" title={t('modes.chat')} aria-label="chat-tab" />
          <Tab
            key="compare"
            title={t('modes.compare')}
            aria-label="compare-tab"
          />
        </Tabs>
        <div className="max-w-full w-full lg:w-auto mt-[-50px] lg:mt-0 lg:ml-auto flex flex-wrap gap-4 items-center">
          <div className="w-full lg:w-auto text-right">
            <Button
              size="md"
              variant="light"
              className="ml-auto lg:ml-0"
              startContent={<IconEraser size={16} stroke="2" />}
              isDisabled={
                firstMessageIsStreaming ||
                secondMessageIsStreaming ||
                (firstConversation.messages.length === 0 &&
                  secondConversation.messages.length === 0)
              }
              aria-label="clear chat"
              onPress={clearAll}
            >
              {t('actions.clearAll')}
            </Button>
          </div>

          <div className="flex gap-2 w-full md:w-[calc(50%-8px)] lg:w-auto">
            <ModelDeploymentSelect
              workloads={workloads}
              onModelDeploymentChange={onFirstModelWorkloadChange}
              selectedModelId={firstModelWorkload?.id}
              label={t('actions.selectModel') ?? ''}
              showOnlyRunningWorkloads={true}
            />
            <Button
              isIconOnly
              variant="light"
              size="md"
              disabled={!firstModelWorkload}
              onPress={() => setFirstSettingsDrawerOpen(true)}
              aria-label="Show Settings"
            >
              <IconSettings
                size="16"
                className={!firstModelWorkload ? 'text-default-500' : ''}
              />
            </Button>
            <SettingsDrawer
              settings={firstSettings}
              onSettingsChange={(settings) => {
                updateSettings(settings, setFirstSettings);
              }}
              showSyncSettings={chatMode === 'compare'}
              syncSettings={syncSettings}
              onSyncSettingsChange={(sync) => {
                setSyncSettings(sync);
                if (sync) {
                  setSecondSettings({ ...firstSettings });
                }
              }}
              selectedModelWorkload={firstModelWorkload}
              isOpen={firstSettingsDrawerOpen}
              onOpenChange={setFirstSettingsDrawerOpen}
            />
          </div>
          {chatMode === 'compare' && (
            <div className="flex gap-2 w-full md:w-[calc(50%-8px)] lg:w-auto">
              <ModelDeploymentSelect
                workloads={workloads}
                onModelDeploymentChange={onSecondModelWorkloadChange}
                selectedModelId={secondModelWorkload?.id}
                label={t('actions.selectModel') ?? ''}
                showOnlyRunningWorkloads={true}
              />
              <Button
                isIconOnly
                variant="light"
                size="md"
                disabled={!secondModelWorkload}
                onPress={() => setSecondSettingsDrawerOpen(true)}
                aria-label="Show Settings"
              >
                <IconSettings
                  size="16"
                  className={!secondModelWorkload ? 'opacity-50' : ''}
                />
              </Button>
              <SettingsDrawer
                settings={secondSettings}
                onSettingsChange={(settings) => {
                  updateSettings(settings, setSecondSettings);
                }}
                showSyncSettings={chatMode === 'compare'}
                syncSettings={syncSettings}
                onSyncSettingsChange={(sync) => {
                  setSyncSettings(sync);
                  if (sync) {
                    setFirstSettings({ ...secondSettings });
                  }
                }}
                selectedModelWorkload={secondModelWorkload}
                isOpen={secondSettingsDrawerOpen}
                onOpenChange={setSecondSettingsDrawerOpen}
              />
            </div>
          )}
        </div>
      </Toolbar>
      <div className="flex w-full h-full overflow-x-scroll overflow-hidden justify-center ">
        {firstConversation.messages.length === 0 && (
          <ChatInfoCard mode={chatMode} />
        )}

        <div
          ref={chatContainerRef1}
          onScroll={handleScroll}
          className={
            'fle pt-6 overflow-y-scroll ' +
            (chatMode != 'compare' ? 'w-full' : 'w-1/2 max-w-[50%]')
          }
        >
          <ChatMessages
            compareMode={chatMode === 'compare'}
            conversation={firstConversation}
            onConversationUpdated={setFirstConversation}
            messagesEndRef={messagesEndRef1}
            loading={firstLoading}
            delayedResponseNotification={firstDelayedResponseNotification}
            messageIsStreaming={firstMessageIsStreaming}
          />
        </div>
        {chatMode === 'compare' && (
          <div
            ref={chatContainerRef2}
            onScroll={handleScroll}
            className="w-1/2 max-w-[50%] pt-6 overflow-y-scroll "
          >
            <ChatMessages
              compareMode={chatMode === 'compare'}
              conversation={secondConversation}
              onConversationUpdated={setSecondConversation}
              messagesEndRef={messagesEndRef2}
              loading={secondLoading}
              delayedResponseNotification={secondDelayedResponseNotification}
              messageIsStreaming={secondMessageIsStreaming}
            />
          </div>
        )}
      </div>

      <BasicChatInput
        content={chatInputContent}
        setContent={setChatInputContent}
        stopConversationRef={stopConversationRef}
        textareaRef={textareaRef}
        onSend={onMessage}
        onScrollDownClick={handleScrollDown}
        showScrollDownButton={showScrollDownButton}
        messageIsStreaming={firstMessageIsStreaming || secondMessageIsStreaming}
        disabled={
          !firstModelWorkload ||
          (chatMode === 'compare' && !secondModelWorkload)
        }
        allowRegenerate={false}
        aria-label="chat-input"
      />
    </div>
  );
};
