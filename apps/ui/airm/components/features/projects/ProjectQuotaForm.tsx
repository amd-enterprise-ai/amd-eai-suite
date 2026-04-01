// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ManagedForm } from '@amdenterpriseai/components';
import { QuotaAllocationEditFields } from '@amdenterpriseai/types';
import {
  ProjectQuotaFormData,
  ProjectWithMembers,
  ProjectWithResourceAllocation,
  UpdateProjectRequest,
} from '@amdenterpriseai/types';
import { convertStringToNumber } from '@amdenterpriseai/utils/app';
import { useTranslation } from 'next-i18next';
import { Alert } from '@amdenterpriseai/components';
import { useCallback, useMemo } from 'react';
import { z } from 'zod';
import { AllocationSettings } from '../quotas';
import { Cluster } from '@amdenterpriseai/types';
import { UpdateQuotaRequest } from '@amdenterpriseai/types';
import { gigabytesToBytes } from '@amdenterpriseai/utils/app';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { APIRequestError } from '@amdenterpriseai/utils/app';
import { useSystemToast } from '@amdenterpriseai/hooks';
import { useAccessControl } from '@/hooks/useAccessControl';
import { updateProject } from '@/services/app';

interface Props {
  project: ProjectWithMembers;
  cluster: Cluster;
}

const tranlationKeySet = 'projects';

export const ProjectQuotaForm: React.FC<Props> = ({ project, cluster }) => {
  const { t } = useTranslation(tranlationKeySet);
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();
  const { isAdministrator } = useAccessControl();

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
      showSubmitButton={isAdministrator}
      showResetButton={isAdministrator}
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
                className="bg-primary/10!"
                description={t('settings.form.guaranteedQuota.info')}
              />
              <AllocationSettings
                form={form}
                quota={project.quota}
                cluster={cluster}
                isReadonly={!isAdministrator}
              />
            </div>
          </section>
        </div>
      )}
    />
  );
};

export default ProjectQuotaForm;
