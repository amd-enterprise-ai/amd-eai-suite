// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SelectItem } from '@heroui/react';
import { IconAlertTriangle, IconCpu } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';
import type { UseFormReturn } from 'react-hook-form';

import { FormSelect } from '@amdenterpriseai/components';

import { ADVANCED_PARAM_AUTOMATIC } from '@/lib/app/aims/filterProfilesByAdvancedParams';
import {
  AIM_PROFILE_TYPE_OPTIMIZED,
  type AIMClusterServiceTemplate,
} from '@/types/aims';

import { UnoptimizedProfileBadge } from './UnoptimizedProfileBadge';

export interface DeployAIMFormValues {
  model: string;
  selectedToken?: string;
  tokenName?: string;
  token?: string;
  imagePullSecrets?: string[];
  metric?: string;
  autoscalingEnabled: boolean;
  minReplicas?: number;
  maxReplicas?: number;
  metricQuery?: string;
  operationOverTime?: string;
  targetType?: string;
  targetValue?: number;
  optimizationClass?: string;
  gpuModel?: string;
  precision?: string;
  gpuCount?: string;
  templateName?: string;
}

export interface DeployAIMAdvancedProfileFieldsProps {
  form: UseFormReturn<DeployAIMFormValues>;
  advancedProfileOptions: {
    optimizationClasses: string[];
    gpuModels: string[];
    precisions: string[];
    gpuCounts: string[];
    profiles: AIMClusterServiceTemplate[];
  };
  filteredProfiles: AIMClusterServiceTemplate[];
  noProfileMatches: boolean;
}

export function DeployAIMAdvancedProfileFields({
  form,
  advancedProfileOptions,
  filteredProfiles,
  noProfileMatches,
}: DeployAIMAdvancedProfileFieldsProps) {
  const { t } = useTranslation('models');

  const profileAutomaticLabel = t(
    'deployAIMDrawer.fields.advancedProfileParams.automaticSelection',
  );
  const profileAutomaticPlaceholder = t(
    'deployAIMDrawer.fields.advancedProfileParams.automaticSelectionFromProfiles',
    { count: filteredProfiles.length },
  );

  const profileSelectPlaceholder = noProfileMatches
    ? t('deployAIMDrawer.fields.advancedProfileParams.noMatchingProfiles')
    : profileAutomaticPlaceholder;

  const profileSelectStartContent = noProfileMatches ? (
    <IconAlertTriangle
      size={18}
      className="shrink-0 text-warning-500"
      aria-hidden
    />
  ) : undefined;

  return (
    <div className="grid grid-cols-2 gap-4 pl-1">
      <FormSelect
        name="optimizationClass"
        form={form}
        label={t(
          'deployAIMDrawer.fields.advancedProfileParams.optimizationClass',
        )}
        aria-label={t(
          'deployAIMDrawer.fields.advancedProfileParams.optimizationClass',
        )}
        placeholder={t(
          'deployAIMDrawer.fields.advancedProfileParams.placeholder',
        )}
        classNames={{
          trigger: 'w-full min-w-0',
          value: 'capitalize',
        }}
      >
        <>
          <SelectItem key={ADVANCED_PARAM_AUTOMATIC}>
            {t('deployAIMDrawer.fields.advancedProfileParams.automatic')}
          </SelectItem>
          {advancedProfileOptions.optimizationClasses.map((value) => (
            <SelectItem key={value} className="capitalize">
              {value}
            </SelectItem>
          ))}
        </>
      </FormSelect>
      <FormSelect
        name="gpuModel"
        form={form}
        label={t('deployAIMDrawer.fields.advancedProfileParams.gpu')}
        aria-label={t('deployAIMDrawer.fields.advancedProfileParams.gpu')}
        placeholder={t(
          'deployAIMDrawer.fields.advancedProfileParams.placeholder',
        )}
        classNames={{ trigger: 'w-full min-w-0' }}
      >
        <>
          <SelectItem key={ADVANCED_PARAM_AUTOMATIC}>
            {t('deployAIMDrawer.fields.advancedProfileParams.automatic')}
          </SelectItem>
          {advancedProfileOptions.gpuModels.map((value) => (
            <SelectItem key={value}>{value}</SelectItem>
          ))}
        </>
      </FormSelect>
      <FormSelect
        name="precision"
        form={form}
        label={t('deployAIMDrawer.fields.advancedProfileParams.precision')}
        aria-label={t('deployAIMDrawer.fields.advancedProfileParams.precision')}
        placeholder={t(
          'deployAIMDrawer.fields.advancedProfileParams.placeholder',
        )}
        classNames={{ trigger: 'w-full min-w-0' }}
      >
        <>
          <SelectItem key={ADVANCED_PARAM_AUTOMATIC}>
            {t('deployAIMDrawer.fields.advancedProfileParams.automatic')}
          </SelectItem>
          {advancedProfileOptions.precisions.map((value) => (
            <SelectItem key={value}>{value}</SelectItem>
          ))}
        </>
      </FormSelect>
      <FormSelect
        name="gpuCount"
        form={form}
        label={t('deployAIMDrawer.fields.advancedProfileParams.gpuCount')}
        aria-label={t('deployAIMDrawer.fields.advancedProfileParams.gpuCount')}
        placeholder={t(
          'deployAIMDrawer.fields.advancedProfileParams.placeholder',
        )}
        classNames={{ trigger: 'w-full min-w-0' }}
      >
        <>
          <SelectItem key={ADVANCED_PARAM_AUTOMATIC}>
            {t('deployAIMDrawer.fields.advancedProfileParams.automatic')}
          </SelectItem>
          {advancedProfileOptions.gpuCounts.map((value) => (
            <SelectItem key={value}>{value}</SelectItem>
          ))}
        </>
      </FormSelect>
      <div className="col-span-2">
        <FormSelect
          name="templateName"
          form={form}
          label={t('deployAIMDrawer.fields.advancedProfileParams.profile')}
          aria-label={t('deployAIMDrawer.fields.advancedProfileParams.profile')}
          placeholder={profileSelectPlaceholder}
          startContent={profileSelectStartContent}
          classNames={{ trigger: 'w-full min-w-0' }}
        >
          <>
            <SelectItem
              key={ADVANCED_PARAM_AUTOMATIC}
              textValue={profileAutomaticLabel}
            >
              {profileAutomaticLabel}
            </SelectItem>
            {filteredProfiles.map((template) => {
              const meta = template.status?.profile?.metadata;
              const isOptimized = meta?.type === AIM_PROFILE_TYPE_OPTIMIZED;
              const gpu = meta?.gpu ?? '—';
              const gpuCount =
                meta?.gpuCount != null
                  ? `${meta.gpuCount} ${meta.gpuCount === 1 ? 'Accelerator' : 'Accelerators'}`
                  : '—';
              const metric = meta?.metric
                ? t(`performanceMetrics.values.${meta.metric}`)
                : '—';
              const precision = meta?.precision ?? '—';
              const row1 = (
                <span className="-ml-1 flex items-center gap-2">
                  <IconCpu size={16} className="shrink-0 text-default-400" />
                  <span>{gpu}</span>
                  <span className="mx-1.5">·</span>
                  <span>{gpuCount}</span>
                </span>
              );
              const row2 = (
                <span className="flex items-center gap-2">
                  <span>{metric}</span>
                  <span className="mx-1.5">·</span>
                  <span>{precision}</span>
                </span>
              );
              const textValue = `${gpu} · ${gpuCount} · ${metric} · ${precision}`;
              return (
                <SelectItem
                  key={template.metadata.name}
                  textValue={textValue}
                  endContent={
                    !isOptimized ? (
                      <UnoptimizedProfileBadge
                        label={t(
                          'deployAIMDrawer.fields.metric.unoptimizedLabel',
                        )}
                      />
                    ) : undefined
                  }
                >
                  <div className="flex flex-col gap-1.5">
                    {row1}
                    <span className="ml-[21px] text-default-500">{row2}</span>
                  </div>
                </SelectItem>
              );
            })}
          </>
        </FormSelect>
      </div>
      <div className="col-span-2">
        <button
          type="button"
          onClick={() => {
            form.setValue('optimizationClass', ADVANCED_PARAM_AUTOMATIC);
            form.setValue('gpuModel', ADVANCED_PARAM_AUTOMATIC);
            form.setValue('precision', ADVANCED_PARAM_AUTOMATIC);
            form.setValue('gpuCount', ADVANCED_PARAM_AUTOMATIC);
            form.setValue('templateName', undefined);
            form.setValue('metric', '');
          }}
          className="cursor-pointer text-sm font-medium text-primary transition-colors hover:underline"
        >
          {t('deployAIMDrawer.fields.advancedProfileParams.resetParameters')}
        </button>
      </div>
    </div>
  );
}
