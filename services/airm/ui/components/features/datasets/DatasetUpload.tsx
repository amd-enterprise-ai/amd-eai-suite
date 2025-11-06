// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Link, SelectItem, Spinner } from '@heroui/react';
import { IconExternalLink } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';
import { FieldValues, Resolver } from 'react-hook-form';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { getDatasets, uploadDataset } from '@/services/app/datasets';
import { useProject } from '@/contexts/ProjectContext';

import { DATASET_FILESIZE_LIMIT } from '@/utils/app/datasets';
import { displayBytesInOptimalUnit } from '@/utils/app/memory';

import {
  DatasetType,
  UploadDatasetFormData,
  UploadDatasetParams,
} from '@/types/datasets';

import {
  FormFileUpload,
  FormInput,
  FormSelect,
} from '@/components/shared/ManagedForm';
import { selectiveZodResolver } from '@/components/shared/ManagedForm/selectiveZodResolver';
import { ModalForm } from '@/components/shared/ModalForm';

import { debounce } from 'lodash';
import { ZodType, z } from 'zod';

interface Props {
  onClose: () => void;
  refresh: () => void;
  isOpen: boolean;
}

export const DatasetUpload = ({ onClose, isOpen, refresh }: Props) => {
  const { toast } = useSystemToast();
  const { t } = useTranslation('datasets');
  const { activeProject } = useProject();
  const queryClient = useQueryClient();

  const [uniqueCheckInProgress, setUniqueCheckInProgress] =
    useState<boolean>(false);

  const { mutate: uploadDatasetMutation, isPending: isUploading } = useMutation(
    {
      mutationFn: ({
        name,
        description,
        datasetType,
        file,
      }: UploadDatasetParams) =>
        uploadDataset(name, description, datasetType, file, activeProject!),
      onSuccess: (): void => {
        toast.success(t('modals.upload.messages.success'));
        refresh();
        onClose();
      },
      onError: (error): void => {
        console.error('Error checking dataset name availability:', error);
        toast.error(t('modals.upload.messages.error'));
      },
    },
  );

  const handleUpload = (data: UploadDatasetFormData): void => {
    uploadDatasetMutation({
      name: data.name,
      description: data.description ?? '',
      datasetType: data.datasetType as DatasetType,
      file: data.file,
    });
  };

  const checkDatasetNameAvailability = useCallback(
    async (name: string, resolve: (result: boolean) => void): Promise<void> => {
      setUniqueCheckInProgress(true);
      try {
        const datasetsWithName = await queryClient.fetchQuery({
          queryKey: ['project', activeProject, 'datasets', { name }],
          queryFn: () => getDatasets(activeProject!, { name }),
          staleTime: 0,
        });
        resolve(datasetsWithName.length === 0);
      } catch (error) {
        console.error('Error checking dataset name availability:', error);
        resolve(true);
      } finally {
        setUniqueCheckInProgress(false);
      }
    },
    [queryClient, activeProject],
  );

  const debouncedCheckDatasetNameAvailability = useMemo(
    () => debounce(checkDatasetNameAvailability, 700),
    [checkDatasetNameAvailability],
  );

  const validateDatasetName = useCallback(
    (desiredName: string): Promise<boolean> => {
      if (!desiredName || desiredName.trim().length === 0)
        return Promise.resolve(false);
      return new Promise((resolve) => {
        debouncedCheckDatasetNameAvailability(desiredName, resolve);
      });
    },
    [debouncedCheckDatasetNameAvailability],
  );

  const formSchema = useMemo(
    () =>
      z.object({
        name: z
          .string()
          .trim()
          .nonempty({
            message: t('modals.upload.form.datasetName.emptyNameError'),
          })
          .regex(/^[0-9A-Za-z-_]+$/, {
            message: t('modals.upload.form.datasetName.invalidCharactersError'),
          })
          .refine(async (name) => validateDatasetName(name), {
            message: t('modals.upload.form.datasetName.nonUniqueNameError'),
          }),
        file: z
          .instanceof(File, {
            message: t('modals.upload.form.fileUpload.emptyError'),
          })
          .refine((file) => file.name.endsWith('.jsonl'), {
            message: t('modals.upload.form.fileUpload.formatError'),
          })
          .refine((file) => file.size <= DATASET_FILESIZE_LIMIT, {
            message: t('modals.upload.form.fileUpload.filesizeError', {
              value: displayBytesInOptimalUnit(DATASET_FILESIZE_LIMIT),
            }),
          }),
        datasetType: z.string().trim(),
        description: z.string().trim().optional(),
      }),
    [t, validateDatasetName],
  );

  return (
    <ModalForm
      isOpen={isOpen}
      title={t('modals.upload.title')}
      confirmText={t('modals.upload.actions.confirm')}
      cancelText={t('modals.upload.actions.cancel')}
      validationSchema={formSchema}
      onCancel={onClose}
      onFormSuccess={(data: FieldValues) => {
        handleUpload(data as UploadDatasetFormData);
      }}
      resolver={selectiveZodResolver as (schema: ZodType) => Resolver}
      isActioning={isUploading}
      renderFields={(form) => (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <p className="text-small dark:text-default-500 text-default-600">
              {t('modals.upload.body')}
            </p>
            <Link
              className="text-small"
              href="https://docs.silogen.ai/core/docs/workbench/training/datasets/?h=datasets#data-formats"
              target="_blank"
            >
              {t('modals.upload.docs')}
              <IconExternalLink size="16" stroke="2" />
            </Link>
          </div>
          <FormInput
            form={form}
            name="name"
            label={t('modals.upload.form.datasetName.label')}
            placeholder={t('modals.upload.form.datasetName.placeholder')}
            data-testid="datasetName"
            isRequired
            endContent={
              uniqueCheckInProgress && <Spinner size="sm" color="primary" />
            }
          />
          <FormSelect
            form={form}
            label={t('modals.upload.form.datasetType.label')}
            placeholder={t('modals.upload.form.datasetType.placeholder')}
            data-testid="datasetSelect"
            disallowEmptySelection
            isRequired
            name="datasetType"
          >
            <SelectItem
              data-testid={`dataset-type-option-finetuning`}
              key={DatasetType.Finetuning}
            >
              {t(`types.${DatasetType.Finetuning}`)}
            </SelectItem>
          </FormSelect>
          <FormInput
            form={form}
            name="description"
            label={t('modals.upload.form.description.label')}
            placeholder={t('modals.upload.form.description.placeholder')}
          />
          <FormFileUpload
            form={form}
            name="file"
            label={t('modals.upload.form.fileUpload.label')}
            placeholder={t('modals.upload.form.fileUpload.placeholder', {
              value: displayBytesInOptimalUnit(DATASET_FILESIZE_LIMIT),
            })}
            accept=".jsonl"
            isRequired
          />
        </div>
      )}
    />
  );
};
