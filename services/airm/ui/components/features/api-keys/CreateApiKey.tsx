// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Selection } from '@heroui/react';
import { Select, SelectItem, Spinner } from '@heroui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Controller } from 'react-hook-form';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import {
  createApiKey,
  fetchApiKeyDetails,
  updateApiKeyBindings,
} from '@/services/app/api-keys';
import { listWorkloads } from '@/services/app/workloads';

import { APIRequestError } from '@/utils/app/errors';
import { displayTimestamp } from '@/utils/app/strings';

import { ApiKey, ApiKeyDetails, ApiKeyWithFullKey } from '@/types/api-keys';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { FormField } from '@/types/forms/forms';
import { Workload } from '@/types/workloads';

import { DrawerForm } from '@/components/shared/DrawerForm';
import { FormFieldComponent } from '@/components/shared/ManagedForm/FormFieldComponent';
import { KeyCreatedDrawer } from './KeyCreatedDrawer';

import { z, ZodType } from 'zod';

interface CreateApiKeyFormData {
  name: string;
  validityPeriod?: string;
  modelDeployments: string[];
}

interface Props {
  isOpen: boolean;
  projectId: string;
  apiKey?: ApiKey;
  onClose: () => void;
}

export const CreateApiKey: React.FC<Props> = ({
  isOpen,
  projectId,
  apiKey,
  onClose,
}) => {
  const { t } = useTranslation('api-keys');
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();
  const isEditMode = !!apiKey;

  const [createdApiKey, setCreatedApiKey] = useState<ApiKeyWithFullKey | null>(
    null,
  );
  const [isKeyCreatedDrawerOpen, setIsKeyCreatedDrawerOpen] = useState(false);
  const [selectedDeployments, setSelectedDeployments] = useState<Selection>(
    new Set([]),
  );

  // Fetch API key details in edit mode to get current group bindings
  const { data: apiKeyDetails, isLoading: isLoadingDetails } =
    useQuery<ApiKeyDetails>({
      queryKey: ['api-key-details', projectId, apiKey?.id],
      queryFn: () => fetchApiKeyDetails(projectId, apiKey!.id),
      enabled: isEditMode && isOpen && !!apiKey?.id,
      refetchOnMount: 'always',
      staleTime: 0,
    });

  const { mutate: createKey, isPending: isCreating } = useMutation({
    mutationFn: async (data: {
      name: string;
      ttl?: string;
      aimIds?: string[];
    }) => {
      return createApiKey(projectId, data);
    },
    onSuccess: (data: ApiKeyWithFullKey) => {
      queryClient.invalidateQueries({
        queryKey: ['project-api-keys', projectId],
      });
      toast.success(t('form.create.notification.success'));
      setCreatedApiKey(data);
      setIsKeyCreatedDrawerOpen(true);
    },
    onError: (error) => {
      toast.error(
        t('form.create.notification.error'),
        error as APIRequestError,
      );
    },
  });

  // Validity period options for API keys (ordered from shortest to longest)
  const validityPeriodOptions = useMemo(
    () => [
      {
        value: '24h',
        label: t('form.create.field.validityPeriod.options.1day'),
      },
      {
        value: '7d',
        label: t('form.create.field.validityPeriod.options.1week'),
      },
      {
        value: '14d',
        label: t('form.create.field.validityPeriod.options.2weeks'),
      },
      {
        value: '30d',
        label: t('form.create.field.validityPeriod.options.30days'),
      },
      {
        value: '60d',
        label: t('form.create.field.validityPeriod.options.60days'),
      },
      {
        value: '90d',
        label: t('form.create.field.validityPeriod.options.90days'),
      },
      {
        value: '0',
        label: t('form.create.field.validityPeriod.options.never'),
      },
    ],
    [t],
  );

  // Mutation for updating API key bindings in edit mode
  const { mutateAsync: updateBindings, isPending: isUpdating } = useMutation({
    mutationFn: async ({ aimIds }: { aimIds: string[] }) => {
      return updateApiKeyBindings(projectId, apiKey!.id, aimIds);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project-api-keys', projectId],
      });
      queryClient.invalidateQueries({
        queryKey: ['api-key-details', projectId, apiKey?.id],
      });
      toast.success(t('form.edit.notification.success'));
      onClose();
    },
    onError: (error) => {
      toast.error(t('form.edit.notification.error'), error as APIRequestError);
    },
  });

  const isPending = isCreating || isUpdating;

  const handleCreateSubmit = useCallback(
    async (data: CreateApiKeyFormData): Promise<void> => {
      if (isEditMode) {
        // Edit mode: only send modelDeployments (aim_ids) to backend
        try {
          await updateBindings({
            aimIds: data.modelDeployments,
          });
        } catch {
          // Error is already handled by mutation's onError callback
          // This catch prevents unhandled promise rejection
        }
      } else {
        // Create mode: create new key with aim_ids
        const payload: { name: string; ttl?: string; aimIds?: string[] } = {
          name: data.name,
          aimIds: data.modelDeployments,
        };

        if (data.validityPeriod) {
          payload.ttl = data.validityPeriod;
        }

        createKey(payload);
      }
    },
    [createKey, updateBindings, isEditMode],
  );

  const handleKeyCreatedDrawerClose = useCallback(() => {
    setIsKeyCreatedDrawerOpen(false);
    setCreatedApiKey(null);
    onClose();
  }, [onClose]);

  const formSchema = useMemo(() => {
    if (isEditMode) {
      // In edit mode, only modelDeployments is required
      return z.object({
        name: z.string().optional(),
        validityPeriod: z.string().optional(),
        modelDeployments: z.array(z.string()).default([]),
      }) as ZodType<CreateApiKeyFormData>;
    }
    // In create mode, name is required
    return z.object({
      name: z
        .string()
        .min(3, t('form.create.field.name.error.minLength'))
        .max(64, t('form.create.field.name.error.maxLength')),
      validityPeriod: z.string().default('0'),
      modelDeployments: z.array(z.string()).default([]),
    }) as ZodType<CreateApiKeyFormData>;
  }, [t, isEditMode]);

  // Fetch deployed model workloads
  const {
    data: workloads = [],
    isLoading: isLoadingWorkloads,
    error: _workloadsError,
  } = useQuery({
    queryKey: ['workloads', projectId, 'inference', 'running'],
    queryFn: () =>
      listWorkloads(projectId, {
        type: [WorkloadType.INFERENCE],
        status: [WorkloadStatus.RUNNING],
        withResources: false,
      }),
    enabled: isOpen, // Fetch for both create and edit modes
  });

  // Transform workloads to model deployment options
  // Only include deployed AIMs (workloads with aimId and clusterAuthGroupId)
  const modelDeployments = useMemo(
    () =>
      workloads
        .filter(
          (workload: Workload) =>
            workload.aimId != null && workload.clusterAuthGroupId != null,
        )
        .map((workload: Workload) => ({
          id: workload.aimId!,
          workloadId: workload.id,
          name: workload.displayName || workload.name,
          groupId: workload.clusterAuthGroupId!,
        })),
    [workloads],
  );

  // Set initial selected deployments in edit mode based on API key groups
  useEffect(() => {
    if (isEditMode && apiKeyDetails && modelDeployments.length > 0) {
      const currentGroups = apiKeyDetails.groups || [];
      const selectedAimIds = modelDeployments
        .filter((deployment) => currentGroups.includes(deployment.groupId))
        .map((deployment) => deployment.id);
      setSelectedDeployments(new Set(selectedAimIds));
    }
  }, [isEditMode, apiKeyDetails, modelDeployments]);

  const formContent: FormField<CreateApiKeyFormData>[] = isEditMode
    ? []
    : [
        {
          name: 'name',
          label: t('form.create.field.name.label'),
          placeholder: t('form.create.field.name.placeholder'),
          isRequired: true,
        },
      ];

  const editModeFields = isEditMode
    ? [
        {
          label: t('form.create.field.name.label'),
          value: apiKeyDetails?.name || apiKey?.name,
        },
        {
          label: t('form.create.field.expiresAt.label'),
          value:
            apiKeyDetails?.expiresAt === null
              ? t('form.create.field.validityPeriod.options.never')
              : apiKeyDetails?.expiresAt
                ? displayTimestamp(new Date(apiKeyDetails.expiresAt))
                : '-',
        },
      ]
    : [];

  const sectionFields = [
    {
      name: 'modelDeployments' as const,
      label: t('form.create.field.modelDeployment.label'),
      placeholder: t('form.create.field.modelDeployment.placeholder'),
      description: t('form.create.field.modelDeployment.description'),
      isRequired: false,
    },
  ];

  const renderLinkedDeployments = () => {
    if (isLoadingDetails || isLoadingWorkloads) {
      return (
        <div className="pl-2">
          <Spinner size="sm" color="default" />
        </div>
      );
    }

    if (selectedDeployments === 'all' || selectedDeployments.size === 0) {
      return (
        <div className="text-sm text-foreground-400 pl-2">
          {t('form.edit.section.noLinkedDeployments')}
        </div>
      );
    }

    const selectedDeploymentsList = Array.from(selectedDeployments)
      .map((aimId) => modelDeployments.find((d) => d.id === aimId))
      .filter((deployment) => deployment != null);

    return (
      <div className="flex flex-col gap-1 pl-2">
        {selectedDeploymentsList.map((deployment) => (
          <div key={deployment!.id} className="text-sm text-foreground">
            • {deployment!.name}
          </div>
        ))}
      </div>
    );
  };

  return (
    <>
      <DrawerForm<CreateApiKeyFormData>
        key={`${isOpen}-${isEditMode ? apiKey?.id : 'create'}`}
        isOpen={isOpen && !isKeyCreatedDrawerOpen}
        isActioning={isPending}
        onFormSuccess={(values) => {
          handleCreateSubmit(values);
          // Don't auto-close in edit mode as the mutation handles it
        }}
        onCancel={onClose}
        title={isEditMode ? t('form.edit.title') : t('form.create.title')}
        confirmText={
          isEditMode
            ? t('form.edit.action.save')
            : t('form.create.action.create')
        }
        cancelText={
          isEditMode
            ? t('form.edit.action.cancel')
            : t('form.create.action.cancel')
        }
        renderFields={(form) => (
          <div className="flex flex-col gap-4">
            {isEditMode &&
              editModeFields.map((field, index) => (
                <div key={index} className="flex flex-col gap-1">
                  <label className="text-sm text-foreground-500">
                    {field.label}
                  </label>
                  <p className="text-foreground">{field.value}</p>
                </div>
              ))}
            {formContent.map((field) => (
              <FormFieldComponent<CreateApiKeyFormData>
                key={field.name}
                formField={field}
                errorMessage={form.formState.errors[field.name]?.message}
                register={form.register}
              />
            ))}
            {!isEditMode && (
              <Controller
                name="validityPeriod"
                control={form.control}
                defaultValue="0"
                render={({ field: controllerField }) => (
                  <Select
                    name={controllerField.name}
                    ref={controllerField.ref}
                    label={t('form.create.field.validityPeriod.label')}
                    placeholder={t(
                      'form.create.field.validityPeriod.placeholder',
                    )}
                    description={t(
                      'form.create.field.validityPeriod.description',
                    )}
                    labelPlacement="outside"
                    variant="bordered"
                    selectedKeys={
                      controllerField.value ? [controllerField.value] : ['0']
                    }
                    onSelectionChange={(keys) => {
                      const selected = Array.from(keys)[0] as string;
                      controllerField.onChange(selected);
                    }}
                  >
                    {validityPeriodOptions.map((option) => (
                      <SelectItem key={option.value}>{option.label}</SelectItem>
                    ))}
                  </Select>
                )}
              />
            )}
            <div className="text-sm font-semibold text-foreground-600 mt-2">
              {t('form.create.section.endpointAccess')}
            </div>
            {sectionFields.map((field) => (
              <Controller
                key={field.name}
                name={field.name}
                control={form.control}
                defaultValue={[]}
                render={({ field: controllerField }) => {
                  // Ensure value is always an array
                  const currentValue = Array.isArray(controllerField.value)
                    ? controllerField.value
                    : [];
                  const selectedKeys = isEditMode
                    ? selectedDeployments
                    : new Set(currentValue);

                  return (
                    <Select
                      name={controllerField.name}
                      ref={controllerField.ref}
                      label={field.label}
                      placeholder={field.placeholder}
                      description={field.description}
                      labelPlacement="outside"
                      variant="bordered"
                      selectionMode="multiple"
                      isLoading={isLoadingWorkloads || isLoadingDetails}
                      isDisabled={isLoadingWorkloads || isLoadingDetails}
                      selectedKeys={selectedKeys}
                      onSelectionChange={(keys) => {
                        const selected = Array.from(keys) as string[];
                        controllerField.onChange(selected);
                        setSelectedDeployments(keys);
                      }}
                      errorMessage={form.formState.errors[field.name]?.message}
                    >
                      {modelDeployments.map((model) => (
                        <SelectItem key={model.id}>{model.name}</SelectItem>
                      ))}
                    </Select>
                  );
                }}
              />
            ))}
            {isEditMode && (
              <div className="flex flex-col gap-1.5">
                <label className="block text-small subpixel-antialiased text-foreground-500">
                  {t('form.edit.section.linkedDeployments')}
                </label>
                {renderLinkedDeployments()}
              </div>
            )}
          </div>
        )}
        validationSchema={formSchema}
      />

      <KeyCreatedDrawer
        isOpen={isKeyCreatedDrawerOpen}
        apiKey={createdApiKey}
        onClose={handleKeyCreatedDrawerClose}
      />
    </>
  );
};

export default CreateApiKey;
