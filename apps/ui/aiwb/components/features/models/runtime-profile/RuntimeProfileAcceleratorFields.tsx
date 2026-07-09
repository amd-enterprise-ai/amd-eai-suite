// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { FormInput, FormSelect, SelectItem } from '@amdenterpriseai/components';
import { useEffect, useMemo } from 'react';
import type { FieldValues, Path, UseFormReturn } from 'react-hook-form';

import {
  getDefaultAcceleratorDeviceId,
  RUNTIME_PROFILE_ACCELERATOR_TYPE_OPTIONS,
  supportedAcceleratorCounts,
  toAcceleratorSelectOptions,
} from '@/lib/app/runtimeProfileCatalog';
import type { ClusterAccelerator } from '@/types/cluster';

type Props<T extends FieldValues> = {
  form: UseFormReturn<T>;
  accelerators: ClusterAccelerator[];
  /**
   * Accelerator counts the base template supports (e.g. `[1,2,4,8]`). When
   * present the count becomes a select limited to these (further capped by the
   * selected device's allocatable count), since aim-engine only emits profiles
   * for these sizes — an in-between value leaves the profile `NotAvailable`.
   * Empty falls back to a free numeric input (base profiles not loaded yet).
   */
  acceleratorCounts?: number[];
  acceleratorTypeField: Path<T>;
  acceleratorField: Path<T>;
  acceleratorCountField: Path<T>;
  acceleratorTypeLabel: string;
  acceleratorTypePlaceholder: string;
  acceleratorLabel: string;
  acceleratorPlaceholder: string;
  acceleratorCountLabel: string;
  isDisabled?: boolean;
};

export function RuntimeProfileAcceleratorFields<T extends FieldValues>({
  form,
  accelerators,
  acceleratorCounts = [],
  acceleratorTypeField,
  acceleratorField,
  acceleratorCountField,
  acceleratorTypeLabel,
  acceleratorTypePlaceholder,
  acceleratorLabel,
  acceleratorPlaceholder,
  acceleratorCountLabel,
  isDisabled = false,
}: Props<T>) {
  const acceleratorOptions = toAcceleratorSelectOptions(accelerators);
  useEffect(() => {
    const defaultDeviceId = getDefaultAcceleratorDeviceId(accelerators);
    const current = form.getValues(acceleratorField) as string;
    if (!current && defaultDeviceId) {
      form.setValue(acceleratorField, defaultDeviceId as never, {
        shouldValidate: true,
      });
    }
  }, [acceleratorField, accelerators, form]);

  // Cap the supported counts by how many of the selected device the cluster can
  // actually allocate; if that filter empties the list (incomplete capacity
  // data), keep the full supported set rather than blocking onboarding.
  const selectedDeviceId = form.watch(acceleratorField) as string | undefined;
  const allocatableCount = useMemo(() => {
    const match = accelerators.find(
      (entry) => entry.deviceId === selectedDeviceId,
    );
    return match?.allocatableCount ?? 0;
  }, [accelerators, selectedDeviceId]);
  const countOptions = useMemo(
    () => supportedAcceleratorCounts(acceleratorCounts, allocatableCount),
    [acceleratorCounts, allocatableCount],
  );

  // Always keep a valid count selected, defaulting to the first option. Covers
  // the initial default and the case where switching devices narrows the
  // options below the current value. shouldDirty:false so it never fabricates
  // an edit (e.g. on edit-mode prefill of a now-unsupported count). The
  // membership guard makes re-running on each render harmless.
  const rawCount = form.watch(acceleratorCountField);
  useEffect(() => {
    if (countOptions.length === 0) {
      return;
    }
    if (countOptions.includes(Number(rawCount))) {
      return;
    }
    // Store the select's string key (downstream normalization coerces to int);
    // a numeric value would not match the string SelectItem keys, leaving the
    // select with nothing highlighted.
    form.setValue(acceleratorCountField, String(countOptions[0]) as never, {
      shouldDirty: false,
    });
  }, [countOptions, rawCount, acceleratorCountField, form]);

  return (
    <>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <FormSelect<T>
          form={form}
          name={acceleratorTypeField}
          label={acceleratorTypeLabel}
          placeholder={acceleratorTypePlaceholder}
          isRequired
          isDisabled={isDisabled}
          data-testid="custom-model-import-accelerator-type"
        >
          <>
            {RUNTIME_PROFILE_ACCELERATOR_TYPE_OPTIONS.map((option) => (
              <SelectItem key={option.key}>{option.label}</SelectItem>
            ))}
          </>
        </FormSelect>
        <FormSelect<T>
          form={form}
          name={acceleratorField}
          label={acceleratorLabel}
          placeholder={acceleratorPlaceholder}
          isRequired
          isDisabled={isDisabled || acceleratorOptions.length === 0}
          data-testid="custom-model-import-accelerator"
        >
          <>
            {acceleratorOptions.map((option) => (
              <SelectItem key={option.key}>{option.label}</SelectItem>
            ))}
          </>
        </FormSelect>
      </div>
      {countOptions.length > 0 ? (
        <FormSelect<T>
          form={form}
          name={acceleratorCountField}
          label={acceleratorCountLabel}
          isRequired
          isDisabled={isDisabled}
          data-testid="custom-model-import-accelerator-count"
        >
          <>
            {countOptions.map((count) => (
              <SelectItem key={String(count)}>{String(count)}</SelectItem>
            ))}
          </>
        </FormSelect>
      ) : (
        <FormInput<T>
          form={form}
          name={acceleratorCountField}
          label={acceleratorCountLabel}
          type="number"
          min={1}
          isRequired
          isDisabled={isDisabled}
          data-testid="custom-model-import-accelerator-count"
        />
      )}
    </>
  );
}
