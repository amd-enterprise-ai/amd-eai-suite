// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { FormSelect, SelectItem } from '@amdenterpriseai/components';
import { useEffect } from 'react';
import type { FieldValues, Path, UseFormReturn } from 'react-hook-form';

import {
  findImageFamily,
  getDefaultImageFamilySelection,
  getFirstSelectableImageFamily,
  getLatestImageTag,
  toSelectableImageSelectOptions,
  toTagSelectOptions,
} from '@/lib/app/runtimeProfileCatalog';
import type { AimImageFamily } from '@/types/cluster';

type Props<T extends FieldValues> = {
  form: UseFormReturn<T>;
  imageFamilies: AimImageFamily[];
  containerImageField: Path<T>;
  containerVersionField: Path<T>;
  containerImageLabel: string;
  containerImagePlaceholder: string;
  containerVersionLabel: string;
  containerVersionPlaceholder: string;
  isDisabled?: boolean;
};

export function RuntimeProfileImageFields<T extends FieldValues>({
  form,
  imageFamilies,
  containerImageField,
  containerVersionField,
  containerImageLabel,
  containerImagePlaceholder,
  containerVersionLabel,
  containerVersionPlaceholder,
  isDisabled = false,
}: Props<T>) {
  const selectedFamilyId = form.watch(containerImageField) as string;
  const imageOptions = toSelectableImageSelectOptions(imageFamilies);
  const tagOptions = toTagSelectOptions(imageFamilies, selectedFamilyId);
  useEffect(() => {
    if (isDisabled || imageFamilies.length === 0) {
      return;
    }

    const currentImage = form.getValues(containerImageField) as string;
    const selectableFamily = getFirstSelectableImageFamily(imageFamilies);
    const shouldApplyCatalogDefault =
      !currentImage ||
      !findImageFamily(imageFamilies, currentImage)?.repository;

    if (shouldApplyCatalogDefault && selectableFamily) {
      const { familyId, tag } = getDefaultImageFamilySelection(imageFamilies);
      if (currentImage !== familyId) {
        form.setValue(containerImageField, familyId as never, {
          shouldValidate: true,
        });
      }
      const currentVersion = form.getValues(containerVersionField) as string;
      if (tag && currentVersion !== tag) {
        form.setValue(containerVersionField, tag as never, {
          shouldValidate: true,
        });
      }
      return;
    }

    const family = findImageFamily(imageFamilies, selectedFamilyId);
    const latestTag = getLatestImageTag(family?.tags ?? []);
    const currentVersion = form.getValues(containerVersionField) as string;
    const versionStillValid = tagOptions.some(
      (option) => option.key === currentVersion,
    );
    if (latestTag && (!currentVersion || !versionStillValid)) {
      form.setValue(containerVersionField, latestTag as never, {
        shouldValidate: true,
      });
    }
  }, [
    containerImageField,
    containerVersionField,
    form,
    imageFamilies,
    isDisabled,
    selectedFamilyId,
    tagOptions,
  ]);
  return (
    <>
      <FormSelect<T>
        form={form}
        name={containerImageField}
        label={containerImageLabel}
        placeholder={containerImagePlaceholder}
        isRequired
        isDisabled={isDisabled}
        data-testid="custom-model-import-container-image"
      >
        <>
          {imageOptions.map((option) => (
            <SelectItem key={option.key}>{option.label}</SelectItem>
          ))}
        </>
      </FormSelect>
      <FormSelect<T>
        form={form}
        name={containerVersionField}
        label={containerVersionLabel}
        placeholder={containerVersionPlaceholder}
        isRequired={tagOptions.length > 0}
        isDisabled={isDisabled || tagOptions.length === 0}
        data-testid="custom-model-import-container-version"
      >
        <>
          {tagOptions.map((option) => (
            <SelectItem key={option.key}>{option.label}</SelectItem>
          ))}
        </>
      </FormSelect>
    </>
  );
}
