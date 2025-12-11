// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem } from '@heroui/react';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';
import { IconCpu } from '@tabler/icons-react';

interface Props {
  selectedModelId?: string;
  workloads: Workload[];
  onModelDeploymentChange: (modelId: string) => void;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  isDisabled?: boolean;
  allowEmptySelection?: boolean;
  showOnlyRunningWorkloads?: boolean;
}

export default function ModelDeploymentSelect({
  selectedModelId,
  onModelDeploymentChange,
  workloads,
  label,
  size,
  isDisabled,
  allowEmptySelection,
  showOnlyRunningWorkloads = true,
}: Props) {
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
    >
      {workloads
        .filter(
          (workload) =>
            (!showOnlyRunningWorkloads ||
              workload.status === WorkloadStatus.RUNNING) &&
            workload.type === WorkloadType.INFERENCE,
        )
        .map((workload) => (
          <SelectItem
            aria-roledescription="option"
            key={workload.id}
            aria-label={workload.id}
          >
            {workload.type === WorkloadType.INFERENCE &&
              (workload.displayName || workload.name)}
          </SelectItem>
        ))}
    </Select>
  );
}
