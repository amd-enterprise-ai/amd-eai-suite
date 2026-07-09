// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';
import type { FieldValues, UseFormReturn } from 'react-hook-form';

import type { RuntimeProfileCatalogState } from '@/hooks/useRuntimeProfileCatalog';
import { canonicalAcceleratorModel } from '@/lib/app/runtimeProfileCatalog';

import { RuntimeProfileAcceleratorFields } from './RuntimeProfileAcceleratorFields';
import { RuntimeProfileCatalogStatus } from './RuntimeProfileCatalogStatus';
import { RuntimeProfileImageFields } from './RuntimeProfileImageFields';
import { RuntimeProfilePrecisionField } from './RuntimeProfilePrecisionField';

type FieldLabels = {
  containerImage: { label: string; placeholder: string };
  containerVersion: { label: string; placeholder: string };
  acceleratorType: { label: string; placeholder: string };
  accelerator: { label: string; placeholder: string };
  acceleratorCount: { label: string };
  modelPrecision: { label: string; placeholder: string };
  catalogLoading: string;
  catalogError: string;
  catalogRetry: string;
  emptyAccelerators: string;
};

type Props<T extends FieldValues> = {
  form: UseFormReturn<T>;
  catalog: RuntimeProfileCatalogState;
  labels: FieldLabels;
  isDisabled?: boolean;
};

export function RuntimeProfileFields<T extends FieldValues>({
  form,
  catalog,
  labels,
  isDisabled = false,
}: Props<T>) {
  const catalogDisabled = isDisabled || catalog.isLoading || catalog.isError;
  const acceleratorsForWizard = useMemo(() => {
    const allowed = catalog.runtimeOptions?.acceleratorModels;
    if (!allowed?.length) {
      return catalog.accelerators;
    }
    const allow = new Set(
      allowed.map((model) => canonicalAcceleratorModel(model.trim())),
    );
    const filtered = catalog.accelerators.filter((entry) =>
      allow.has(canonicalAcceleratorModel(entry.productName)),
    );
    return filtered.length > 0 ? filtered : catalog.accelerators;
  }, [catalog.accelerators, catalog.runtimeOptions?.acceleratorModels]);
  return (
    <div className="flex flex-col gap-4">
      <RuntimeProfileCatalogStatus
        isLoading={catalog.isLoading}
        isError={catalog.isError}
        errorMessage={catalog.error?.message}
        showEmptyAcceleratorsWarning={
          !catalog.isLoading &&
          !catalog.isError &&
          acceleratorsForWizard.length === 0
        }
        emptyAcceleratorsMessage={labels.emptyAccelerators}
        loadingMessage={labels.catalogLoading}
        loadErrorMessage={labels.catalogError}
        retryLabel={labels.catalogRetry}
        onRetry={catalog.invalidateCatalog}
      />
      {!catalog.isLoading && !catalog.isError && (
        <>
          <RuntimeProfileImageFields<T>
            form={form}
            imageFamilies={catalog.imageFamilies}
            containerImageField={'containerImage' as never}
            containerVersionField={'containerVersion' as never}
            containerImageLabel={labels.containerImage.label}
            containerImagePlaceholder={labels.containerImage.placeholder}
            containerVersionLabel={labels.containerVersion.label}
            containerVersionPlaceholder={labels.containerVersion.placeholder}
            isDisabled={catalogDisabled}
          />
          <RuntimeProfileAcceleratorFields<T>
            form={form}
            accelerators={acceleratorsForWizard}
            acceleratorCounts={catalog.runtimeOptions?.acceleratorCounts ?? []}
            acceleratorTypeField={'acceleratorType' as never}
            acceleratorField={'accelerator' as never}
            acceleratorCountField={'acceleratorCount' as never}
            acceleratorTypeLabel={labels.acceleratorType.label}
            acceleratorTypePlaceholder={labels.acceleratorType.placeholder}
            acceleratorLabel={labels.accelerator.label}
            acceleratorPlaceholder={labels.accelerator.placeholder}
            acceleratorCountLabel={labels.acceleratorCount.label}
            isDisabled={catalogDisabled}
          />
          <RuntimeProfilePrecisionField<T>
            form={form}
            precisionField={'modelPrecision' as never}
            precisionLabel={labels.modelPrecision.label}
            precisionPlaceholder={labels.modelPrecision.placeholder}
            isDisabled={catalogDisabled}
            options={(catalog.runtimeOptions?.precisions ?? []).map(
              (precision) => ({ key: precision, label: precision }),
            )}
          />
        </>
      )}
    </div>
  );
}
