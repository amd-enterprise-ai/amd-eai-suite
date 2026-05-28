// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SelectItem, Spinner } from '@heroui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  createApiKey,
  fetchApiKeyDetails,
  updateApiKeyBindings,
} from '@/lib/app/api-keys';

import { APIRequestError } from '@amdenterpriseai/utils/app';
import { displayTimestamp } from '@amdenterpriseai/utils/app';

import { ApiKey } from '@/types/api-keys';
import { ApiKeyDetails, ApiKeyWithFullKey } from '@/types/api-keys';

import {
  Alert,
  DrawerForm,
  FormInput,
  FormSelect,
} from '@amdenterpriseai/components';
import { KeyCreatedDrawer } from './KeyCreatedDrawer';

import { z, ZodType } from 'zod';
import {
  fetchProfilesForServices,
  getAimClusterModels,
  getAimServices,
  resolveAIMServiceDisplay,
} from '@/lib/app/aims';
import type { AIMServiceProfile } from '@/lib/app/aims';
import { formatModelDeploymentSubtitle } from '@/lib/app/modelDeploymentDisplay';
import { AIMService, AIMServiceStatus } from '@/types/aims';

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
  const { t } = useTranslation(['api-keys', 'models']);
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();
  const isEditMode = !!apiKey;

  const [createdApiKey, setCreatedApiKey] = useState<ApiKeyWithFullKey | null>(
    null,
  );
  const [isKeyCreatedDrawerOpen, setIsKeyCreatedDrawerOpen] = useState(false);

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
    const modelDeploymentsField = z.preprocess((val: unknown) => {
      if (Array.isArray(val)) return val;
      if (typeof val === 'string' && val !== '') return val.split(',');
      return [];
    }, z.array(z.string()));

    if (isEditMode) {
      // In edit mode, only modelDeployments is required
      return z.object({
        name: z.string().optional(),
        validityPeriod: z.string().optional(),
        modelDeployments: modelDeploymentsField.default([]),
      }) as ZodType<CreateApiKeyFormData>;
    }
    // In create mode, name is required
    return z.object({
      name: z
        .string()
        .min(3, t('form.create.field.name.error.minLength'))
        .max(64, t('form.create.field.name.error.maxLength')),
      validityPeriod: z.string().default('0'),
      modelDeployments: modelDeploymentsField.default([]),
    }) as ZodType<CreateApiKeyFormData>;
  }, [t, isEditMode]);

  const { data: aimServices = [], isLoading: isLoadingAimServices } = useQuery({
    queryKey: ['aim-services', projectId],
    queryFn: () => getAimServices(projectId),
    enabled: isOpen && !!projectId,
  });

  const { data: aimServiceProfiles = new Map<string, AIMServiceProfile>() } =
    useQuery({
      queryKey: [
        'aim-service-profiles',
        projectId,
        aimServices.map((s: AIMService) => s.id),
      ],
      queryFn: () => fetchProfilesForServices(aimServices),
      enabled: isOpen && aimServices.length > 0,
    });

  const { data: parsedAIMs } = useQuery({
    queryKey: ['parsed-aims', projectId],
    queryFn: async () => {
      const response = await getAimClusterModels(projectId);
      return response;
    },
    enabled: isOpen,
  });

  const modelDeployments = useMemo(() => {
    return aimServices
      .filter(
        (service: AIMService) =>
          service.id != null &&
          service.status.status === AIMServiceStatus.RUNNING &&
          service.endpoints?.external != null &&
          service.clusterAuthGroupId != null,
      )
      .map((service: AIMService) => {
        const displayInfo = resolveAIMServiceDisplay(service, parsedAIMs);
        const profile = aimServiceProfiles.get(String(service.id));
        const title =
          `${displayInfo.canonicalName} ${displayInfo.imageVersion ? `(${displayInfo.imageVersion})` : ''}`.trim();
        const subtitle = formatModelDeploymentSubtitle(t, {
          metric: profile?.metric ?? String(displayInfo.metric),
          gpu: profile?.gpu,
          templateGpuCount: profile?.templateGpuCount,
          precision: profile?.precision,
        });
        return {
          id: service.id!,
          workloadId: service.id!,
          title,
          subtitle,
          groupId: service.clusterAuthGroupId!,
        };
      });
  }, [aimServices, aimServiceProfiles, parsedAIMs, t]);

  const defaultValues = useMemo((): CreateApiKeyFormData => {
    if (!isEditMode) {
      return { name: '', validityPeriod: '0', modelDeployments: [] };
    }
    if (!apiKeyDetails || modelDeployments.length === 0) {
      return {
        name: apiKeyDetails?.name ?? apiKey?.name ?? '',
        validityPeriod: '0',
        modelDeployments: [],
      };
    }
    const selectedAimIds = modelDeployments
      .filter((d) => apiKeyDetails.groups?.includes(d.groupId))
      .map((d) => d.id);
    return {
      name: apiKeyDetails.name ?? apiKey?.name ?? '',
      validityPeriod: '0',
      modelDeployments: selectedAimIds,
    };
  }, [isEditMode, apiKeyDetails, modelDeployments, apiKey?.name]);

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

  const renderLinkedDeployments = (
    selectedAimIdsRaw: string[] | Set<string> | undefined,
  ): React.ReactNode => {
    const selectedAimIds = Array.isArray(selectedAimIdsRaw)
      ? selectedAimIdsRaw
      : selectedAimIdsRaw instanceof Set
        ? Array.from(selectedAimIdsRaw)
        : [];

    if (isLoadingDetails || isLoadingAimServices) {
      return (
        <div className="pl-2">
          <Spinner size="sm" color="default" />
        </div>
      );
    }

    if (!selectedAimIds.length) {
      return (
        <div className="text-sm text-foreground-400 pl-2">
          {t('form.edit.section.noLinkedDeployments')}
        </div>
      );
    }

    const selectedDeploymentsList = selectedAimIds
      .map((aimId) => modelDeployments?.find((d) => d.id === aimId))
      .filter(
        (deployment): deployment is NonNullable<typeof deployment> =>
          deployment != null,
      );

    return (
      <div className="flex flex-col gap-1 pl-2">
        {selectedDeploymentsList.map((deployment) => (
          <div key={deployment.id} className="text-sm text-foreground">
            <div>• {deployment.title}</div>
            {deployment.subtitle !== '' && (
              <div className="text-tiny text-default-500 pl-3">
                {deployment.subtitle}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <>
      <DrawerForm<CreateApiKeyFormData>
        key={`create-api-key-${projectId}-${isEditMode ? apiKey?.id : 'new'}-${apiKeyDetails ? 'loaded' : 'pending'}`}
        isOpen={isOpen && !isKeyCreatedDrawerOpen}
        isActioning={isPending}
        onFormSuccess={(values) => {
          handleCreateSubmit(values);
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
        defaultValues={defaultValues}
        validationSchema={formSchema}
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
            {!isEditMode && (
              <>
                <FormInput<CreateApiKeyFormData>
                  form={form}
                  name="name"
                  label={t('form.create.field.name.label')}
                  placeholder={t('form.create.field.name.placeholder')}
                  isRequired
                />
                <FormSelect<CreateApiKeyFormData>
                  form={form}
                  name="validityPeriod"
                  label={t('form.create.field.validityPeriod.label')}
                  placeholder={t(
                    'form.create.field.validityPeriod.placeholder',
                  )}
                  description={t(
                    'form.create.field.validityPeriod.description',
                  )}
                >
                  {validityPeriodOptions.map((option) => (
                    <SelectItem key={option.value}>{option.label}</SelectItem>
                  ))}
                </FormSelect>
              </>
            )}
            <div className="text-sm font-semibold text-foreground-600 mt-2">
              {t('form.create.section.endpointAccess')}
            </div>
            <FormSelect<CreateApiKeyFormData>
              form={form}
              name="modelDeployments"
              label={t('form.create.field.modelDeployment.label')}
              placeholder={t('form.create.field.modelDeployment.placeholder')}
              description={t('form.create.field.modelDeployment.description')}
              selectionMode="multiple"
              isLoading={isLoadingAimServices || isLoadingDetails}
              isDisabled={isLoadingAimServices || isLoadingDetails}
            >
              {modelDeployments.map((d) => (
                <SelectItem
                  key={d.id}
                  textValue={`${d.title} ${d.subtitle}`}
                  description={d.subtitle || undefined}
                  classNames={{
                    description: 'text-default-500',
                  }}
                >
                  {d.title}
                </SelectItem>
              ))}
            </FormSelect>
            {isEditMode && (
              <>
                <div className="flex flex-col gap-1.5">
                  <label className="block text-small subpixel-antialiased text-foreground-500">
                    {t('form.edit.section.linkedDeployments')}
                  </label>
                  {renderLinkedDeployments(
                    form.watch('modelDeployments') ?? [],
                  )}
                </div>
                <Alert
                  color="warning"
                  hideIconWrapper={true}
                  description={t('form.edit.warning.linkedDeploymentsWarning')}
                />
              </>
            )}
          </div>
        )}
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
