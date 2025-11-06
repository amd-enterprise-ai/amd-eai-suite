// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { AvailableChartColorsKeys } from '@/utils/app/tremor-charts/utils';

import { WorkloadStatus } from '@/types/enums/workloads';
import { ProjectStatusCount } from '@/types/metrics';

import { CategorySplitStatsCard } from '@/components/shared/Metrics/CategorySplitStatsCard';

interface Props {
  projectName: string;
  totalWorkloads: number;
  data: ProjectStatusCount[];
  isLoading?: boolean;
}

const workloadStatusColorMap: Record<WorkloadStatus, AvailableChartColorsKeys> =
  {
    [WorkloadStatus.FAILED]: 'red',
    [WorkloadStatus.PENDING]: 'gray',
    [WorkloadStatus.RUNNING]: 'blue',
    [WorkloadStatus.COMPLETE]: 'green',
    [WorkloadStatus.DELETE_FAILED]: 'amber',
    [WorkloadStatus.TERMINATED]: 'gray',
    [WorkloadStatus.UNKNOWN]: 'darkgray',
    [WorkloadStatus.DELETED]: 'emerald',
    [WorkloadStatus.ADDED]: 'cyan',
    [WorkloadStatus.DELETING]: 'fuchsia',
    [WorkloadStatus.DOWNLOADING]: 'violet',
  };

export const ProjectWorkloadsStatsCard: React.FC<Props> = ({
  data,
  projectName,
  totalWorkloads,
  isLoading,
}) => {
  const { t } = useTranslation('projects');
  const { t: workloadsT } = useTranslation('workloads');

  return (
    <div className="flex grow">
      <CategorySplitStatsCard
        title={
          <div className="flex gap-2 items-center font-light text-nowrap">
            {t('dashboard.overview.workloadStates.title')}
            <span className="font-bold">{projectName}</span>
          </div>
        }
        total={
          <div className="flex gap-2 items-end font-light text-nowrap">
            <span className="text-2xl font-bold">{totalWorkloads}</span>
            <span className="mb-0.5">
              {t('dashboard.overview.workloadStates.total')}
            </span>
          </div>
        }
        data={
          data
            ? {
                title: t('dashboard.overview.workloadStates.subtitle'),
                total: totalWorkloads,
                values: data.map((status) => ({
                  label: workloadsT(`status.${status.status}`),
                  value: status.count,
                  color: workloadStatusColorMap[status.status],
                })),
              }
            : null
        }
        isLoading={isLoading}
      />
    </div>
  );
};

export default ProjectWorkloadsStatsCard;
