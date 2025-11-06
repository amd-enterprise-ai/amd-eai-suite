// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Accordion, AccordionItem } from '@heroui/react';
import { IconInfoCircle } from '@tabler/icons-react';
import React from 'react';

import { useTranslation } from 'next-i18next';

import { DebugInfo, Message } from '@/types/chat';

import { Modal } from '@/components/shared/Modal/Modal';

import { MemoizedChatMessage } from './MemoizedChatMessage';

interface DebugInfoModalProps {
  debugInfo: DebugInfo;
  onClose: () => void;
  isOpen: boolean;
}

export const DebugInfoModal: React.FC<DebugInfoModalProps> = ({
  debugInfo,
  onClose,
  isOpen,
}) => {
  const { t } = useTranslation('chat');

  return (
    <>
      {isOpen && (
        <Modal
          onClose={onClose}
          title={t('debugInfoModal.title') || ''}
          subTitle={t('debugInfoModal.subTitle') || ''}
          size="3xl"
        >
          <div>
            <Accordion>
              <AccordionItem title={t('debugInfoModal.ragDocumentsTitle')}>
                <div className="mb-6 p-6 rounded-md bg-primary-200 text-primary-900">
                  <IconInfoCircle className="inline mr-1.5 text-primary" />
                  {t('debugInfoModal.ragDocumentsDescription')}
                </div>
                <div>
                  {!!debugInfo.sources ? (
                    debugInfo.sources.map((source, index) => (
                      <div
                        key={index}
                        className="mb-6 p-6 bg-default-100 rounded-md"
                      >
                        <div className="flex items-left">
                          <span className="rounded font-semibold">
                            {index + 1}. {source.sourceId}
                          </span>
                        </div>
                        <div className="mb-4">
                          <a href={source.url} className=" hover:underline">
                            {source.url}
                          </a>
                        </div>
                        <div className=" rounded-xl ">{source.text}</div>
                        <div className="mt-6">
                          <span className="font-semibold mr-1">Score:</span>
                          &nbsp;
                          <span className="bg-secondary rounded px-2 py-1 text-sm font-bold text-white">
                            {source.score || source.score == 0
                              ? source.score.toFixed(2)
                              : 'N/A'}
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div>{t('debugInfoModal.noSources')}</div>
                  )}
                </div>
              </AccordionItem>
              <AccordionItem title={t('debugInfoModal.promptsTitle')}>
                <div className="mb-6 p-6 rounded-md bg-primary-200 text-primary-900">
                  <IconInfoCircle className="inline mr-1.5 text-primary" />
                  {t('debugInfoModal.promptsDescription')}
                </div>
                <div className="mb-6 p-6 bg-default-100 rounded-md">
                  {!!debugInfo.messages ? (
                    debugInfo.messages.map(
                      (message: Message, index: number) => (
                        <MemoizedChatMessage
                          key={index}
                          message={message}
                          showCursorOnMessage={false}
                          allowEdit={false}
                          allowCopy={false}
                        />
                      ),
                    )
                  ) : (
                    <div>{t('debugInfoModal.noPromptMessages')}</div>
                  )}
                </div>
              </AccordionItem>
              <AccordionItem title={t('debugInfoModal.tokenUsageTitle')}>
                {debugInfo.usage ? (
                  <div>
                    <div>
                      <span className="font-semibold text-default-800">
                        {t('debugInfoModal.promptTokens')}
                      </span>
                      &nbsp;
                      <span className="rounded px-2 py-1 dark:text-default-500 text-default-600">
                        {debugInfo.usage.prompt_tokens}
                      </span>
                    </div>
                    <div>
                      <span className="font-semibold text-default-800">
                        {t('debugInfoModal.completionTokens')}
                      </span>
                      &nbsp;
                      <span className=" rounded px-2 py-1 dark:text-default-500 text-default-600">
                        {debugInfo.usage.completion_tokens}
                      </span>
                    </div>
                    <div>
                      <span className="font-semibold text-default-800">
                        {t('debugInfoModal.totalTokens')}
                      </span>
                      &nbsp;
                      <span className="rounded px-2 py-1 dark:text-default-500 text-default-600">
                        {debugInfo.usage.total_tokens}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-default-600 italic">
                    {t('debugInfoModal.noTokenUsage')}
                  </div>
                )}
              </AccordionItem>
            </Accordion>
          </div>
        </Modal>
      )}
    </>
  );
};
