// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Alert,
  FormInput,
  FormTextarea,
  Input,
} from '@amdenterpriseai/components';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';
import type { UseFormReturn } from 'react-hook-form';

import { normalizeCustomModelDisplayName } from '@/lib/app/custom-models';

import type { ModelSourcePreviewResponse } from '@/types/model-import';

import type { CustomModelImportFormValues } from '../types';

interface Props {
  form: UseFormReturn<CustomModelImportFormValues>;
  preview: ModelSourcePreviewResponse | undefined;
  existingDisplayNames: Set<string>;
}

/**
 * Step 2 — show the read-only canonical name resolved from the source and
 * let the user override the display properties (display name, description,
 * tags). All three are seeded from the upstream preview by the parent page;
 * the display name is a free-form, human-readable label (not a K8s name), so
 * the user may keep the suggested value or replace it with any non-empty text.
 */
export const StepModelInformation = ({
  form,
  preview,
  existingDisplayNames,
}: Props) => {
  const { t } = useTranslation('models', {
    keyPrefix: 'customModels.import.steps.information',
  });

  const canonicalName = preview?.repoId ?? form.watch('source') ?? '';
  const displayName = form.watch('displayName') ?? '';
  const isDuplicateName = existingDisplayNames.has(
    normalizeCustomModelDisplayName(displayName),
  );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold">{t('title')}</h2>
      </header>

      <Input
        label={t('fields.canonicalName.label')}
        labelPlacement="outside"
        variant="faded"
        value={canonicalName}
        isReadOnly
        data-testid="custom-model-import-canonical-name"
      />

      <section className="flex flex-col gap-4">
        <header className="flex flex-col gap-1">
          <h3 className="text-base font-semibold">
            {t('displayProperties.title')}
          </h3>
          <p className="text-sm text-default-500">
            {t('displayProperties.subtitle')}
          </p>
        </header>

        <FormInput<CustomModelImportFormValues>
          form={form}
          name="displayName"
          label={t('fields.displayName.label')}
          placeholder={t('fields.displayName.placeholder')}
          isRequired
          data-testid="custom-model-import-display-name"
        />

        {isDuplicateName && (
          <Alert
            color="warning"
            variant="flat"
            icon={<IconAlertTriangle />}
            title={t('fields.displayName.duplicateWarning.title')}
            description={t('fields.displayName.duplicateWarning.description')}
            data-testid="custom-model-import-duplicate-name-warning"
          />
        )}

        <FormTextarea<CustomModelImportFormValues>
          form={form}
          name="description"
          label={t('fields.description.label')}
          placeholder={t('fields.description.placeholder')}
        />

        <FormInput<CustomModelImportFormValues>
          form={form}
          name="tagsInput"
          label={t('fields.tags.label')}
          placeholder={t('fields.tags.placeholder')}
          description={t('fields.tags.description')}
        />
      </section>
    </div>
  );
};

export default StepModelInformation;
