// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody, CardHeader } from '@heroui/react';
import { IconCalendar } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';

import {
  displayTimestamp,
  formatDurationFromSeconds,
} from '@amdenterpriseai/utils/app';

interface WorkloadTimelineCardProps {
  createdAt: string;
  updatedAt: string;
  queueTime?: number;
  runningTime?: number;
}

export const WorkloadTimelineCard: React.FC<WorkloadTimelineCardProps> = ({
  createdAt,
  updatedAt,
  queueTime,
  runningTime,
}) => {
  const { t } = useTranslation('workloads');

  return (
    <Card className="border border-default-200 shadow-sm rounded-sm dark:bg-default-100">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <IconCalendar size={18} className="text-default-400" />
          <span className="text-sm font-medium">
            {t('details.sections.timeline')}
          </span>
        </div>
      </CardHeader>
      <CardBody className="pt-0 space-y-3 text-sm">
        <div className="space-y-0.5">
          <div className="text-default-500">
            {t('details.fields.createdAt')}
          </div>
          <div>{displayTimestamp(new Date(createdAt))}</div>
        </div>
        <div className="space-y-0.5">
          <div className="text-default-500">
            {t('details.fields.updatedAt')}
          </div>
          <div>{displayTimestamp(new Date(updatedAt))}</div>
        </div>
        <div className="space-y-0.5">
          <div className="text-default-500">
            {t('details.fields.queueTime')}
          </div>
          <div>
            {queueTime != null ? formatDurationFromSeconds(queueTime) : '—'}
          </div>
        </div>
        <div className="space-y-0.5">
          <div className="text-default-500">
            {t('details.fields.runningTime')}
          </div>
          <div>
            {runningTime != null ? formatDurationFromSeconds(runningTime) : '—'}
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
