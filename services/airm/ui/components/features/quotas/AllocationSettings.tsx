// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow,
  cn,
} from '@heroui/react';
import { useMemo } from 'react';
import { UseFormReturn } from 'react-hook-form';

import { useTranslation } from 'next-i18next';

import { bytesToGigabytes } from '@/utils/app/memory';
import { displayFixedNumber } from '@/utils/app/strings';

import { Cluster } from '@/types/clusters';
import { QuotaResource } from '@/types/enums/quotas';
import { QuotaAllocationEditFields } from '@/types/enums/quotas-form-fields';
import { Quota } from '@/types/quotas';

import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';
import { SliderInput } from '@/components/shared/SliderInput';
import { ProjectQuotaFormData } from '@/types/projects';

interface Props {
  form: UseFormReturn<ProjectQuotaFormData>;
  quota: Quota;
  cluster?: Cluster;
}

type SettingField = {
  id: string;
  name: QuotaAllocationEditFields;
  label: string;
  availableToAllocate: number;
  displayCapacityUnit?: boolean;
  step?: number;
  disabled?: boolean;
};

const translationKeySet = 'projects';

const restrictToPositive = (value: number) => Math.max(value, 0);

export const AllocationSettings: React.FC<Props> = ({
  form,
  quota,
  cluster,
}) => {
  const { t } = useTranslation(translationKeySet);

  const settings: SettingField[] = useMemo(() => {
    return [
      {
        id: 'gpu',
        name: QuotaAllocationEditFields.GPU,
        label: t('settings.form.guaranteedQuota.fields.gpu'),
        availableToAllocate: cluster?.gpuInfo
          ? restrictToPositive(
              cluster.availableResources[QuotaResource.GPU] -
                cluster.allocatedResources[QuotaResource.GPU] +
                (quota ? quota[QuotaResource.GPU] : 0),
            )
          : 0,
        disabled: !cluster?.gpuInfo,
      },
      {
        id: 'cpu',
        name: QuotaAllocationEditFields.CPU,
        label: t('settings.form.guaranteedQuota.fields.cpu'),
        availableToAllocate: cluster
          ? restrictToPositive(
              (cluster.availableResources[QuotaResource.CPU] -
                cluster.allocatedResources[QuotaResource.CPU] +
                (quota ? quota[QuotaResource.CPU] : 0)) /
                1000,
            )
          : 0,
      },
      {
        id: 'ram',
        name: QuotaAllocationEditFields.RAM,
        label: t('settings.form.guaranteedQuota.fields.ram'),
        availableToAllocate: cluster
          ? bytesToGigabytes(
              restrictToPositive(
                cluster.availableResources[QuotaResource.RAM] -
                  cluster.allocatedResources[QuotaResource.RAM] +
                  (quota ? quota[QuotaResource.RAM] : 0),
              ),
            )
          : 0,
        displayCapacityUnit: true,
      },
      {
        id: 'disk',
        name: QuotaAllocationEditFields.DISK,
        label: t('settings.form.guaranteedQuota.fields.disk'),
        availableToAllocate: cluster
          ? bytesToGigabytes(
              restrictToPositive(
                cluster.availableResources[QuotaResource.DISK] -
                  cluster.allocatedResources[QuotaResource.DISK] +
                  (quota ? quota[QuotaResource.DISK] : 0),
              ),
            )
          : 0,
        displayCapacityUnit: true,
      },
    ];
  }, [quota, cluster, t]);

  return (
    <Table
      aria-label={t('settings.form.guaranteedQuota.title') || ''}
      classNames={{
        wrapper: 'shadow-none p-0',
        table: 'table-fixed w-full',
        th: 'uppercase',
      }}
    >
      <TableHeader>
        <TableColumn className="w-36">
          {t('settings.form.guaranteedQuota.groups.resource')}
        </TableColumn>
        <TableColumn>
          {t('settings.form.guaranteedQuota.groups.allocation')}
        </TableColumn>
        <TableColumn className="w-36 whitespace-normal">
          {t('settings.form.guaranteedQuota.groups.available')}
        </TableColumn>
      </TableHeader>
      <TableBody items={settings}>
        {(item: SettingField) => (
          <TableRow
            key={item.id}
            className={cn({
              'text-foreground': item.disabled,
              'text-opacity-disabled': item.disabled,
            })}
          >
            <TableCell className="max-w-1/4">{item.label}</TableCell>
            <TableCell>
              <FormFieldComponent<ProjectQuotaFormData>
                formField={{
                  name: item.name,
                  label: item.label,
                  component: SliderInput,
                  props: {
                    min: 0,
                    max: item.availableToAllocate,
                    ariaLabel: item.label,
                    step: item.step,
                    disabled: item.disabled,
                    id: item.name,
                  },
                }}
                register={form.register}
                defaultValue={form?.formState?.defaultValues?.[item.name]}
              />
            </TableCell>
            <TableCell>
              {`${displayFixedNumber(item.availableToAllocate)} ${
                item.displayCapacityUnit ? 'GB' : ''
              }`}
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
};

export default AllocationSettings;
