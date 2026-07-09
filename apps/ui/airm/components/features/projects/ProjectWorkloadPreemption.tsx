// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  SelectItem,
  FormNumberInput,
  FormSelect,
  FormSwitch,
  Tooltip,
} from '@amdenterpriseai/components';
import { IconInfoCircle } from '@tabler/icons-react';
import type { TFunction } from 'i18next';
import type { UseFormReturn } from 'react-hook-form';

import { GpuPreemptionPolicy } from '@/types/enums/gpu-preemption-policy';
import { ProjectGpuPreemptionFormFields } from '@/types/enums/project-form-fields';
import { CreateProjectFormData } from '@/types/projects';

export interface ProjectWorkloadPreemptionProps {
  form: UseFormReturn<CreateProjectFormData>;
  t: TFunction;
}

export function ProjectWorkloadPreemption({
  form,
  t,
}: ProjectWorkloadPreemptionProps) {
  const enabled = form.watch(ProjectGpuPreemptionFormFields.ENABLED);

  return (
    <div className="flex flex-col gap-4 border-t border-default-200 pt-4">
      <div className="flex items-center gap-1">
        <h3 className="text-small font-semibold text-foreground">
          {t('modal.create.form.preemption.sectionTitle')}
        </h3>
        <Tooltip
          classNames={{
            content: 'max-w-md',
          }}
          content={t('modal.create.form.preemption.tooltip')}
          placement="top"
        >
          <button
            type="button"
            className="inline-flex cursor-pointer rounded-small border-0 bg-transparent p-0 text-default-400 outline-offset-2 hover:opacity-80"
            aria-label={t('modal.create.form.preemption.tooltipTriggerAria')}
          >
            <IconInfoCircle size={16} aria-hidden />
          </button>
        </Tooltip>
      </div>
      <FormSwitch
        form={form}
        name={ProjectGpuPreemptionFormFields.ENABLED}
        aria-label={t('modal.create.form.preemption.toggle')}
      >
        {t('modal.create.form.preemption.toggle')}
      </FormSwitch>
      {/* Unmount when off so fields unregister (shouldUnregister). Remount reuses useForm defaultValues — no effect needed to seed policy/threshold/grace. */}
      {enabled ? (
        <div className="flex flex-col gap-4">
          <FormSelect
            form={form}
            name={ProjectGpuPreemptionFormFields.POLICY}
            label={t('modal.create.form.preemption.policy.label')}
            placeholder={t('modal.create.form.preemption.policy.placeholder')}
            isRequired
            disallowEmptySelection
          >
            <SelectItem key={GpuPreemptionPolicy.OnPressure}>
              {t('modal.create.form.preemption.policy.onPressure')}
            </SelectItem>
            <SelectItem key={GpuPreemptionPolicy.Always}>
              {t('modal.create.form.preemption.policy.always')}
            </SelectItem>
          </FormSelect>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-4">
            <div className="min-w-0">
              <FormNumberInput
                form={form}
                name={ProjectGpuPreemptionFormFields.THRESHOLD}
                label={t('modal.create.form.preemption.threshold.label')}
                minValue={0}
                maxValue={100}
                isRequired
                endContent={
                  <span className="text-small text-default-500">%</span>
                }
              />
            </div>
            <div className="min-w-0">
              <FormNumberInput
                form={form}
                name={ProjectGpuPreemptionFormFields.GRACE_PERIOD}
                label={t('modal.create.form.preemption.gracePeriod.label')}
                description={t(
                  'modal.create.form.preemption.gracePeriod.description',
                )}
                isRequired
                endContent={
                  <span className="text-small text-default-500">
                    {t('modal.create.form.preemption.gracePeriod.suffix')}
                  </span>
                }
              />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
