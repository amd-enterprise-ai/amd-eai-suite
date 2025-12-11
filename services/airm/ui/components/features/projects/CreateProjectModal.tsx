// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem } from '@heroui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

import { useTranslation } from 'next-i18next';
import router from 'next/router';

import useSystemToast from '@/hooks/useSystemToast';

import { createProject } from '@/services/app/projects';

import { APIRequestError } from '@/utils/app/errors';
import { gigabytesToBytes } from '@/utils/app/memory';
import { getProjectEditUrl } from '@/utils/app/projects';

import { Cluster } from '@/types/clusters';
import { ProjectFormFields } from '@/types/enums/project-form-fields';
import {
  BaseProjectFormData,
  CreateProjectRequest,
  ProjectWithResourceAllocation,
} from '@/types/projects';
import { UpdateQuotaRequest } from '@/types/quotas';

import { DrawerForm } from '@/components/shared/Drawer';
import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';

import { ZodType, z } from 'zod';

interface Props {
  clusters: Cluster[];
  isOpen: boolean;
  onProjectCreate: (projectId: string) => void;
  onOpenChange: () => void;
  projects: ProjectWithResourceAllocation[];
}

const CreateProjectModal: React.FC<Props> = ({
  clusters,
  isOpen,
  onOpenChange,
  onProjectCreate,
  projects,
}) => {
  const i18nKeySet = 'projects';
  const { t } = useTranslation(i18nKeySet);
  const { toast } = useSystemToast();

  const onboardedClusters = useMemo(
    () => clusters.filter((c) => c.status !== 'verifying'),
    [clusters],
  );

  const queryClient = useQueryClient();
  // 1000 allowed by kaiwo - 1 for the default catchall quota
  const MAX_PROJECTS_IN_CLUSTER = 999;

  const ProjectSchema: ZodType<BaseProjectFormData> = useMemo(
    () =>
      z.object({
        [ProjectFormFields.NAME]: z
          .string()
          .trim()
          .min(2, t('modal.create.form.name.validation.length') || '')
          .max(41, t('modal.create.form.name.validation.length') || '')
          .regex(
            /^[a-z0-9]([-a-z0-9]*[a-z0-9])?$/,
            t('modal.create.form.name.validation.format') || '',
          )
          .refine(
            (name) =>
              !projects.some(
                (g) => g.name.toLowerCase() === name.toLowerCase(),
              ),
            {
              message: t('modal.create.form.name.validation.unique') || '',
            },
          ),
        [ProjectFormFields.DESCRIPTION]: z
          .string()
          .trim()
          .min(2, t('modal.create.form.description.validation.length') || '')
          .max(
            1024,
            t('modal.create.form.description.validation.length') || '',
          ),
        [ProjectFormFields.CLUSTER_ID]: z
          .string()
          .trim()
          .refine(
            (clusterId) => {
              const count = projects.filter(
                (p) => p.clusterId === clusterId,
              ).length;
              return count < MAX_PROJECTS_IN_CLUSTER;
            },
            {
              message:
                t('modal.create.form.cluster.validation.exceedProjectsCount', {
                  num: MAX_PROJECTS_IN_CLUSTER,
                }) || '',
            },
          ),
      }),
    [t, projects],
  );

  const { mutate: createProjectMutation, isPending } = useMutation<
    ProjectWithResourceAllocation,
    Error,
    CreateProjectRequest
  >({
    mutationFn: createProject,
    onSuccess: (newProject) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['quotas'] });
      toast.success(t('modal.create.notification.success'));

      onProjectCreate(newProject.id);
      router.push(getProjectEditUrl(newProject.id));
    },
    onError: (error) => {
      toast.error(
        t('modal.create.notification.error'),
        error as APIRequestError,
      );
      console.error('Error saving project:', error);
    },
  });

  const handleFormSuccess = useCallback(
    (data: BaseProjectFormData) => {
      const formData = data as BaseProjectFormData;
      const description = (
        formData[ProjectFormFields.DESCRIPTION] as string
      ).trim();
      const name = (formData[ProjectFormFields.NAME] as string).trim();
      const clusterId = formData[ProjectFormFields.CLUSTER_ID] as string;

      const quota: UpdateQuotaRequest = {
        cpu_milli_cores: 0,
        memory_bytes: gigabytesToBytes(0),
        ephemeral_storage_bytes: gigabytesToBytes(0),
        gpu_count: 0,
      };

      createProjectMutation({
        name: name,
        description: description,
        cluster_id: clusterId,
        quota: quota,
      } as CreateProjectRequest);
    },
    [createProjectMutation],
  );

  return (
    <DrawerForm<BaseProjectFormData>
      isOpen={isOpen}
      isActioning={isPending}
      title={t('modal.create.title')}
      onOpenChange={onOpenChange}
      onFormSuccess={handleFormSuccess}
      onCancel={onOpenChange}
      validationSchema={ProjectSchema}
      cancelText={t('modal.create.actions.cancel')}
      confirmText={t('modal.create.actions.confirm')}
      renderFields={(form) => {
        return (
          <div className="flex flex-col gap-4">
            <FormFieldComponent<BaseProjectFormData>
              formField={{
                name: ProjectFormFields.NAME,
                label: t('modal.create.form.name.label'),
                placeholder: t('modal.create.form.name.placeholder'),
                description: t('modal.create.form.name.description'),
                isRequired: true,
                props: {
                  maxLength: 41,
                },
              }}
              errorMessage={
                form.formState.errors[ProjectFormFields.NAME]?.message
              }
              register={form.register}
            />
            <FormFieldComponent<BaseProjectFormData>
              formField={{
                name: ProjectFormFields.DESCRIPTION,
                label: t('modal.create.form.description.label'),
                isRequired: true,
                placeholder: t('modal.create.form.description.placeholder'),
                props: {
                  maxLength: 1024,
                },
              }}
              errorMessage={
                form.formState.errors[ProjectFormFields.DESCRIPTION]?.message
              }
              register={form.register}
            />
            <FormFieldComponent<BaseProjectFormData>
              formField={{
                name: ProjectFormFields.CLUSTER_ID,
                label: t('modal.create.form.cluster.label'),
                placeholder: t('modal.create.form.cluster.placeholder'),
                component: (formElemProps) => (
                  <Select
                    data-testid="cluster-select"
                    labelPlacement="outside"
                    placeholder={t('modal.create.form.cluster.placeholder')}
                    variant="bordered"
                    disabledKeys={onboardedClusters
                      .filter((c) => c.status === 'unhealthy')
                      .map((c) => c.id)}
                    selectedKeys={formElemProps?.value}
                    disallowEmptySelection
                    {...formElemProps}
                  >
                    {onboardedClusters.map((cluster: Cluster) => (
                      <SelectItem data-testid={cluster.id} key={cluster.id}>
                        {cluster.name}
                      </SelectItem>
                    ))}
                  </Select>
                ),
              }}
              errorMessage={
                form.formState.errors[ProjectFormFields.CLUSTER_ID]?.message
              }
              register={form.register}
            />
          </div>
        );
      }}
    ></DrawerForm>
  );
};

export default CreateProjectModal;
