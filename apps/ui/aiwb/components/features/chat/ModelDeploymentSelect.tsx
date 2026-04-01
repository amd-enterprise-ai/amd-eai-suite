// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';
import { Select, SelectItem } from '@heroui/react';
import { IconCpu } from '@tabler/icons-react';

import { Workload, WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';

interface Props {
  selectedModelId?: string;
  workloads: Workload[];
  onModelDeploymentChange: (modelId: string) => void;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  isDisabled?: boolean;
  allowEmptySelection?: boolean;
  showOnlyRunningWorkloads?: boolean;
  workloadDescriptions?: Record<string, string>;
}

export function ModelDeploymentSelect({
  selectedModelId,
  onModelDeploymentChange,
  workloads,
  label,
  size,
  isDisabled,
  allowEmptySelection,
  showOnlyRunningWorkloads = true,
  workloadDescriptions,
}: Props) {
  const filteredWorkloads = useMemo(
    () =>
      workloads.filter(
        (workload) =>
          (!showOnlyRunningWorkloads ||
            workload.status === WorkloadStatus.RUNNING) &&
          workload.type === WorkloadType.INFERENCE,
      ),
    [workloads, showOnlyRunningWorkloads],
  );

  return (
    <Select
      className="select-wrapper w-full lg:min-w-72"
      data-testid="model-deployment-select"
      aria-label={label}
      placeholder={label}
      disallowEmptySelection={!allowEmptySelection}
      selectedKeys={selectedModelId ? [selectedModelId] : []}
      onChange={(e) => onModelDeploymentChange(e.target.value)}
      isDisabled={workloads.length === 0 || isDisabled}
      size={size || 'md'}
      startContent={<IconCpu size={16} />}
      renderValue={(items) => {
        return items.map((item) => {
          const workload = filteredWorkloads.find((w) => w.id === item.key);
          const workloadLabel = workload?.displayName ?? workload?.name;
          const description = workload
            ? workloadDescriptions?.[workload.id]
            : undefined;

          return (
            <div key={item.key} className="flex flex-col">
              <span>{workloadLabel}</span>
              {description != null && description !== '' && (
                <span className="text-default-500 text-tiny">
                  {description}
                </span>
              )}
            </div>
          );
        });
      }}
    >
      {filteredWorkloads.map((workload) => (
        <SelectItem
          aria-roledescription="option"
          key={workload.id}
          aria-label={workload.id}
          description={workloadDescriptions?.[workload.id]}
        >
          {workload.displayName ?? workload.name}
        </SelectItem>
      ))}
    </Select>
  );
}

export default ModelDeploymentSelect;
