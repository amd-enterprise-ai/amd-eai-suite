// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody } from '@heroui/react';
import { IconExternalLink } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';

import type { DocEntry } from './documentation-mapping';

type RelevantDocsCardProps = DocEntry;

export const RelevantDocsCard = ({
  title,
  description,
  url,
}: RelevantDocsCardProps) => {
  const { t } = useTranslation('sharedComponents', {
    keyPrefix: 'RelevantDocs',
  });
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="group h-full block"
    >
      <Card
        className="dark:bg-default-100/50 p-2 h-full flex flex-col group-hover:bg-default-200/30 group-hover:dark:bg-default-100/70 transition-colors"
        shadow="sm"
        radius="md"
      >
        <CardBody className=" flex flex-col gap-2 flex-1 min-h-0">
          <h3 className="text-sm font-semibold text-inherit group-hover:text-primary">
            {title}
          </h3>
          <p className="text-xs opacity-80">{description}</p>
          <div className="text-xs opacity-80 flex items-center gap-1 mt-auto">
            {t('learnMore')}
            <span className="inline-flex">
              <IconExternalLink size={14} />
            </span>
          </div>
        </CardBody>
      </Card>
    </a>
  );
};

RelevantDocsCard.displayName = 'RelevantDocsCard';
