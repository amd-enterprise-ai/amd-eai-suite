// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ManagedForm } from '@/components/shared/ManagedForm';
import { QuotaAllocationEditFields } from '@/types/enums/quotas-form-fields';
import {
  ProjectQuotaFormData,
  ProjectWithMembers,
  ProjectWithResourceAllocation,
  UpdateProjectRequest,
} from '@/types/projects';
import { convertStringToNumber } from '@/utils/app/strings';
import { Alert } from '@heroui/react';
import { useTranslation } from 'next-i18next';
import { useCallback, useMemo } from 'react';
import { z } from 'zod';
import { AllocationSettings } from '../quotas';
import { Cluster } from '@/types/clusters';
import { UpdateQuotaRequest } from '@/types/quotas';
import { gigabytesToBytes } from '@/utils/app/memory';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { APIRequestError } from '@/utils/app/errors';
import useSystemToast from '@/hooks/useSystemToast';
import { updateProject } from '@/services/app/projects';

interface Props {
  project: ProjectWithMembers;
  cluster: Cluster;
}

const tranlationKeySet = 'projects';

export const ProjectQuotaForm: React.FC<Props> = ({ project, cluster }) => {
  const { t } = useTranslation(tranlationKeySet);
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const defaultValues = {
    [QuotaAllocationEditFields.CPU]: project.quota.cpuMilliCores / 1000,
    [QuotaAllocationEditFields.GPU]: project.quota.gpuCount,
    [QuotaAllocationEditFields.RAM]: Math.floor(
      project.quota.memoryBytes / (1024 * 1024 * 1024),
    ),
    [QuotaAllocationEditFields.DISK]: Math.floor(
      project.quota.ephemeralStorageBytes / (1024 * 1024 * 1024),
    ),
  };

  const formSchema = useMemo(
    () =>
      z.object({
        [QuotaAllocationEditFields.CPU]: z
          .preprocess((val) => {
            return convertStringToNumber(val as string);
          }, z.number())
          .default(0),
        [QuotaAllocationEditFields.GPU]: z.preprocess((val) => {
          return convertStringToNumber(val as string);
        }, z.number()),
        [QuotaAllocationEditFields.RAM]: z.preprocess((val) => {
          return convertStringToNumber(val as string);
        }, z.number()),
        [QuotaAllocationEditFields.DISK]: z.preprocess((val) => {
          return convertStringToNumber(val as string);
        }, z.number()),
      }) as z.ZodType<ProjectQuotaFormData, z.ZodTypeDef, ProjectQuotaFormData>,
    [],
  );

  const { mutate: updateProjectMutation, isPending: isUpdatingProject } =
    useMutation<ProjectWithResourceAllocation, Error, UpdateProjectRequest>({
      mutationFn: updateProject,
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['project'] });
        queryClient.invalidateQueries({ queryKey: ['cluster'] });
        toast.success(t('settings.form.notification.success'));
      },
      onError: (error) => {
        toast.error(error.message, error as APIRequestError);
        console.error('Error saving project', error);
      },
    });

  // Unified handler for both basic info and quota forms
  const handleFormSubmit = useCallback(
    (data: ProjectQuotaFormData) => {
      const quota: UpdateQuotaRequest = {
        cpu_milli_cores: data[QuotaAllocationEditFields.CPU] * 1000,
        memory_bytes: gigabytesToBytes(data[QuotaAllocationEditFields.RAM]),
        ephemeral_storage_bytes: gigabytesToBytes(
          data[QuotaAllocationEditFields.DISK],
        ),
        gpu_count: data[QuotaAllocationEditFields.GPU] ?? 0,
      };

      updateProjectMutation({
        ...project,
        quota: quota,
      });
    },
    [project, updateProjectMutation],
  );

  return (
    <ManagedForm<ProjectQuotaFormData>
      isActioning={isUpdatingProject}
      className="flex flex-col w-full"
      defaultValues={defaultValues}
      validationSchema={formSchema}
      showSubmitButton={true}
      showResetButton={true}
      submitButtonText={t('settings.form.actions.confirm')!}
      resetButtonText={t('settings.form.actions.reset')!}
      onFormSuccess={handleFormSubmit}
      renderFields={(form) => (
        <div className="w-full flex flex-col">
          <section id="guaranteed-quota">
            <div className="flex flex-col gap-6 my-3">
              <Alert
                color="primary"
                hideIconWrapper={true}
                className="!bg-primary/10"
              >
                {t('settings.form.guaranteedQuota.info')}
              </Alert>
              <AllocationSettings
                form={form}
                quota={project.quota}
                cluster={cluster}
              />
            </div>
          </section>
        </div>
      )}
    />
  );
};

export default ProjectQuotaForm;
