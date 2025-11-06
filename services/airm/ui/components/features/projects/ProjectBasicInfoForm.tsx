// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// SPDX-FileCopyrightText: 2024 The AIRM Authors
//
// SPDX-License-Identifier: MIT

import { ManagedForm } from '@/components/shared/ManagedForm';
import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';
import useSystemToast from '@/hooks/useSystemToast';
import { updateProject } from '@/services/app/projects';
import { ProjectFormFields } from '@/types/enums/project-form-fields';
import { FormField } from '@/types/forms/forms';
import {
  ProjectGeneralFormData,
  ProjectWithMembers,
  ProjectWithResourceAllocation,
  UpdateProjectRequest,
} from '@/types/projects';
import { Select, SelectItem } from '@heroui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'next-i18next';
import { useCallback, useMemo } from 'react';
import { z, ZodType } from 'zod';
import { getCluster as fetchCluster } from '@/services/app/clusters';
import { APIRequestError } from '@/utils/app/errors';
import { Cluster } from '@/types/clusters';

interface Props {
  project: ProjectWithMembers;
  cluster: Cluster;
}

export const ProjectBasicInfoForm: React.FC<Props> = ({ project, cluster }) => {
  const { t } = useTranslation('projects');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const defaultValues = {
    [ProjectFormFields.NAME]: project.name,
    [ProjectFormFields.DESCRIPTION]: project.description,
    [ProjectFormFields.CLUSTER_ID]: project.clusterId,
  };

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

  const { data: clusterData } = useQuery<Cluster>({
    queryKey: ['cluster'],
    queryFn: () => fetchCluster(cluster.id as string),
    initialData: cluster,
  });

  const formSchema: ZodType<ProjectGeneralFormData> = useMemo(
    () =>
      z.object({
        [ProjectFormFields.NAME]: z.string(),
        [ProjectFormFields.DESCRIPTION]: z
          .string()
          .trim()
          .min(
            2,
            t('settings.form.basicInfo.description.validation.length') || '',
          )
          .max(
            1024,
            t('settings.form.basicInfo.description.validation.length') || '',
          ),
        [ProjectFormFields.CLUSTER_ID]: z.string().trim(),
      }),
    [t],
  );

  const projectFormFields: FormField<ProjectGeneralFormData>[] = [
    {
      name: ProjectFormFields.NAME,
      label: t('settings.form.basicInfo.name.label'),
      isReadOnly: true,
    },
    {
      name: ProjectFormFields.DESCRIPTION,
      label: t('settings.form.basicInfo.description.label'),
      isRequired: true,
      placeholder: t('settings.form.basicInfo.description.placeholder'),
      props: {
        maxLength: 1024,
      },
    },
    {
      name: ProjectFormFields.CLUSTER_ID,
      label: t('settings.form.basicInfo.cluster.label'),
      isRequired: false,
      component: (formElemProps) => (
        <Select
          data-testid="cluster-select"
          labelPlacement="outside"
          variant="bordered"
          selectedKeys={formElemProps?.value}
          defaultSelectedKeys={[clusterData.id]}
          {...formElemProps}
          isDisabled
        >
          <SelectItem data-testid={clusterData.id} key={clusterData.id}>
            {clusterData.name}
          </SelectItem>
        </Select>
      ),
    },
  ];

  const handleFormSubmit = useCallback(
    (data: ProjectGeneralFormData) => {
      const projectDescription = (
        data[ProjectFormFields.DESCRIPTION] as string
      ).trim();

      updateProjectMutation({
        id: project.id,
        description: projectDescription,
        quota: {
          cpu_milli_cores: project.quota.cpuMilliCores,
          gpu_count: project.quota.gpuCount,
          memory_bytes: project.quota.memoryBytes,
          ephemeral_storage_bytes: project.quota.ephemeralStorageBytes,
        },
      });
    },
    [project, updateProjectMutation],
  );

  return (
    <ManagedForm<ProjectGeneralFormData>
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
          <section id="basic-info">
            <div className="flex flex-col gap-6 my-3">
              <div className="flex flex-col gap-4">
                {projectFormFields.map((field) => (
                  <FormFieldComponent<ProjectGeneralFormData>
                    key={field.name}
                    formField={field}
                    errorMessage={form.formState.errors[field.name]?.message}
                    register={form.register}
                    defaultValue={
                      defaultValues[field.name as keyof ProjectGeneralFormData]
                    }
                  />
                ))}
              </div>
            </div>
          </section>
        </div>
      )}
    />
  );
};

export default ProjectBasicInfoForm;
