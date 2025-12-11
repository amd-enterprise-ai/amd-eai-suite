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
              <AccordionItem title={t('debugInfoModal.promptsTitle')}>
                <div className="mb-6 p-6 rounded-md bg-primary-200 text-primary-900">
                  <IconInfoCircle className="inline mr-1.5 text-primary" />
                  {t('debugInfoModal.promptsDescription')}
                </div>
                <div className="mb-6 p-6 bg-default-100 rounded-md">
                  {debugInfo.messages && debugInfo.messages.length > 0 ? (
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
