// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Divider, FormInput, Input } from '@amdenterpriseai/components';
import { useTranslation } from 'next-i18next';
import { Controller, type UseFormReturn } from 'react-hook-form';

import { ProjectHuggingFaceTokenSelector } from '@/components/shared/HuggingFaceTokenSelector/ProjectHuggingFaceTokenSelector';

import type { CustomModelImportFormValues } from '../types';

interface Props {
  form: UseFormReturn<CustomModelImportFormValues>;
  namespace: string;
  /**
   * Edit mode: the import source and HF token are immutable post-onboard, so
   * the source field is disabled (and read-only) and the token selector is
   * hidden (the wizard also skips the preview call entirely).
   */
  readOnly?: boolean;
}

/**
 * Step 1 — collect the upstream model source URL and (optionally) a
 * Hugging Face token. The wizard host calls `previewModelSource` with
 * these values before advancing to step 2. In edit mode the source is shown
 * read-only since the import identity cannot change.
 */
export const StepModelSource = ({
  form,
  namespace,
  readOnly = false,
}: Props) => {
  const { t } = useTranslation('models', {
    keyPrefix: 'customModels.import.steps.source',
  });

  if (readOnly) {
    return (
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h2 className="text-xl font-semibold">{t('title')}</h2>
          <p className="text-sm text-default-500">{t('readOnlyDescription')}</p>
        </header>

        <Input
          label={t('fields.source.label')}
          labelPlacement="outside"
          variant="bordered"
          value={form.watch('source') ?? ''}
          isReadOnly
          isDisabled
          data-testid="custom-model-import-source"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold">{t('title')}</h2>
        <p className="text-sm text-default-500">{t('description')}</p>
      </header>

      <FormInput<CustomModelImportFormValues>
        form={form}
        name="source"
        label={t('fields.source.label')}
        placeholder={t('fields.source.placeholder')}
        description={t('fields.source.description')}
        isRequired
        data-testid="custom-model-import-source"
      />

      <Divider />

      <div className="flex flex-col gap-3">
        <header className="flex flex-col gap-1">
          <h3 className="text-base font-semibold">
            {t('fields.huggingFace.title')}
          </h3>
          <p className="text-sm text-default-500">
            {t('fields.huggingFace.description')}
          </p>
        </header>

        <Controller
          control={form.control}
          name="hfTokenSecretName"
          render={({ field, fieldState }) => (
            <ProjectHuggingFaceTokenSelector
              namespace={namespace}
              value={field.value || null}
              onChange={field.onChange}
              isInvalid={Boolean(fieldState.error?.message)}
              errorMessage={fieldState.error?.message}
            />
          )}
        />
      </div>
    </div>
  );
};

export default StepModelSource;
