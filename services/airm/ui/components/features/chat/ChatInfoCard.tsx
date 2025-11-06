// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody } from '@heroui/react';
import { IconBubbleText, IconGitCompare } from '@tabler/icons-react';

import { useTranslation } from 'next-i18next';

interface Props {
  mode: 'chat' | 'compare';
}

const ChatInfoCard = ({ mode }: Props) => {
  const { t } = useTranslation('chat');

  return (
    <Card className="hidden md:block fixed top-1/2 max-w-[600px] mx-8 p-8 shadow-none -translate-y-1/2 border border-default-200 dark:border-default-300">
      <CardBody className="flex flex-col gap-3 items-start">
        <div className="flex items-center gap-3 mb-2">
          <span className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900">
            {mode === 'chat' ? (
              <IconBubbleText
                size={28}
                className="text-primary-600 dark:text-primary-300"
              />
            ) : (
              <IconGitCompare
                size={28}
                className="text-primary-600 dark:text-primary-300"
              />
            )}
          </span>
          <h2 className="font-bold text-2xl text-default-800">
            {t(`${mode}.title`)}
          </h2>
        </div>
        <p className="mb-3">{t(`${mode}.description`)}</p>
        <ul className="list-disc pl-4 text-default-600 text-sm space-y-1 mb-1">
          <li>{t(`${mode}.tips.tip1`)}</li>
          <li>{t(`${mode}.tips.tip2`)}</li>
        </ul>
      </CardBody>
    </Card>
  );
};

export default ChatInfoCard;
