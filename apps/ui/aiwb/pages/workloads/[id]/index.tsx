// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Input,
  Skeleton,
} from '@heroui/react';
import {
  IconArrowLeft,
  IconExternalLink,
  IconMessage,
  IconFileText,
  IconTrash,
  IconCopy,
  IconInfoCircle,
  IconServer,
  IconCalendar,
  IconDatabase,
  IconWorld,
  IconCircleCheck,
} from '@tabler/icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import { useState, useMemo, useRef } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  getWorkload,
  deleteWorkload,
  getWorkloadMetrics,
} from '@/lib/app/workloads';
import { getModel } from '@/lib/app/models';
import { getDataset } from '@/lib/app/datasets';
import { getChart } from '@/lib/app/charts';

import {
  getCurrentTimeRange,
  getWorkloadStatusVariants,
} from '@amdenterpriseai/utils/app';
import { getWorkloadTypeVariants } from '@amdenterpriseai/utils/app';
import { authOptions } from '@amdenterpriseai/utils/server';

import {
  TimeRangePeriod,
  TimeSeriesResponse,
  WorkloadStatus,
  WorkloadType,
} from '@amdenterpriseai/types';

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import {
  StatusDisplay,
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
} from '@amdenterpriseai/components';
import { displayMegabytesInGigabytes } from '@amdenterpriseai/utils/app';

import InferenceMetrics from '@/components/features/workloads/InferenceMetrics';
import { aiWorkbenchMenuItems } from '@amdenterpriseai/utils/app';
import { get } from 'lodash';
import { useProject } from '@/contexts/ProjectContext';
import { TimeRange } from '@/types/metrics';
import LoadingState from '@/components/shared/PageErrorHandler/LoadingState';
import ErrorMessage from '@/components/shared/PageErrorHandler/ErrorMessage';

const WorkloadDetailsPage: React.FC = () => {
  const { t } = useTranslation(['workloads', 'common']);
  const { toast } = useSystemToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id } = router.query;
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const { activeProject } = useProject();

  const [timeRange, setTimeRange] = useState<TimeRange>(
    getCurrentTimeRange(TimeRangePeriod['15M']),
  );

  const {
    data: workload,
    isLoading: isWorkloadLoading,
    isError: isWorkloadError,
    refetch: refetchWorkload,
  } = useQuery({
    queryKey: ['workload', id],
    queryFn: () => getWorkload(id as string, activeProject!),
    refetchInterval: 30000,
    enabled: !!id && !!activeProject,
  });

  const { data: gpuDeviceUtilization } = useQuery<TimeSeriesResponse>({
    queryKey: [
      'workload',
      id,
      'metrics',
      'gpu_device_utilization',
      timeRange.start?.toISOString(),
      timeRange.end?.toISOString(),
    ],
    queryFn: () =>
      getWorkloadMetrics(
        id as string,
        activeProject!,
        timeRange.start,
        timeRange.end,
        'gpu_device_utilization',
      ),
    enabled: !!id && !!activeProject,
  });

  const gpuDeviceValues = gpuDeviceUtilization?.data?.[0]?.values;
  const latestGpuDeviceUtilizationValue = gpuDeviceValues?.length
    ? gpuDeviceValues[gpuDeviceValues.length - 1]?.value
    : undefined;

  const { data: gpuMemoryUtilization } = useQuery<TimeSeriesResponse>({
    queryKey: [
      'workload',
      id,
      'metrics',
      'gpu_memory_utilization',
      timeRange.start?.toISOString(),
      timeRange.end?.toISOString(),
    ],
    queryFn: () =>
      getWorkloadMetrics(
        id as string,
        activeProject!,
        timeRange.start,
        timeRange.end,
        'gpu_memory_utilization',
      ),
    enabled: !!id && !!activeProject,
  });

  const gpuMemoryValues = gpuMemoryUtilization?.data?.[0]?.values;
  const latestGpuMemoryUtilizationValue = gpuMemoryValues?.length
    ? gpuMemoryValues[gpuMemoryValues.length - 1]?.value
    : undefined;

  const { data: model, isLoading: isLoadingModel } = useQuery({
    queryKey: ['model', activeProject, workload?.modelId],
    queryFn: () => getModel(workload!.modelId!, activeProject!),
    enabled: !!workload?.modelId && !!activeProject,
  });

  const { data: dataset, isLoading: isLoadingDataset } = useQuery({
    queryKey: ['dataset', activeProject, workload?.datasetId],
    queryFn: () => getDataset(workload!.datasetId!, activeProject!),
    enabled: !!workload?.datasetId && !!activeProject,
    retry: false,
  });

  const { data: chart, isLoading: isLoadingChart } = useQuery({
    queryKey: ['chart', activeProject, workload?.chartId],
    queryFn: () => getChart(workload!.chartId!),
    enabled: !!workload?.chartId,
  });

  const canOpenWorkspace =
    workload?.type === WorkloadType.WORKSPACE &&
    workload?.status === WorkloadStatus.RUNNING &&
    workload.endpoints?.external;

  const canOpenChat =
    workload?.type === WorkloadType.INFERENCE &&
    workload.status === WorkloadStatus.RUNNING;

  const canDelete = workload?.status !== WorkloadStatus.DELETED;

  const hasOutputData =
    workload?.endpoints &&
    (workload.endpoints.external || workload.endpoints.internal);

  // For inference workloads, append the API endpoint path
  const isInferenceWorkload = workload?.type === WorkloadType.INFERENCE;

  const { mutate: deleteWorkloadMutation } = useMutation({
    mutationFn: (id: string) => deleteWorkload(id, activeProject!),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['workload', id, activeProject],
      });
      toast.success(t('list.actions.delete.notification.success'));
      router.back();
    },
    onError: () => {
      toast.error(t('list.actions.delete.notification.error'));
    },
  });

  const statusVariants = useMemo(() => getWorkloadStatusVariants(t), [t]);
  const typeVariants = useMemo(() => getWorkloadTypeVariants(t), [t]);

  const handleCopyToClipboard = (text: string, fieldName: string) => {
    if (!navigator.clipboard) return;

    navigator.clipboard.writeText(text).then(() => {
      setCopiedField(fieldName);
      setTimeout(() => {
        setCopiedField(null);
      }, 2000);
    });
  };
  const launchWorkload = (status: WorkloadStatus) => {
    const isRunning = status === WorkloadStatus.RUNNING;

    if (!isRunning) {
      toast.error(t('list.errors.noRunningWorkload'));
      return;
    }

    const url = workload?.endpoints?.external || '';
    window.open(url, '_blank');
  };

  const handleBack = () => {
    router.back();
  };

  const handleOpenChat = () => {
    router.push(`/chat?workload=${workload?.id}`);
  };

  const getEndpointUrl = (baseUrl: string) => {
    return isInferenceWorkload
      ? `${baseUrl}/v1/chat/completions`
      : baseUrl || '';
  };

  return isWorkloadLoading ? (
    <LoadingState />
  ) : isWorkloadError || !workload ? (
    <ErrorMessage onRefresh={refetchWorkload} />
  ) : (
    <div className="flex flex-col space-y-6 py-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="flat"
            onPress={handleBack}
            size="sm"
            isIconOnly
            startContent={<IconArrowLeft size={16} />}
          ></Button>
          <div className="flex items-center space-x-3 pr-2">
            <h2>{workload.displayName || workload.name}</h2>
            <StatusDisplay
              type={workload.status}
              variants={statusVariants}
              additionalProps={{ isShowBackground: true, isTextColored: true }}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-2">
          {canOpenWorkspace && (
            <Button
              color="primary"
              variant="flat"
              onPress={() => launchWorkload(workload.status)}
              startContent={<IconExternalLink size={16} />}
            >
              {t('list.actions.openWorkspace.label')}
            </Button>
          )}

          {canOpenChat && (
            <Button
              color="default"
              variant="flat"
              onPress={handleOpenChat}
              startContent={<IconMessage size={16} />}
            >
              {t('list.actions.chat.label')}
            </Button>
          )}

          <Button
            color="default"
            variant="flat"
            onPress={() => setIsLogsModalOpen(true)}
            startContent={<IconFileText size={16} />}
          >
            {t('list.actions.logs.label')}
          </Button>

          {canDelete && (
            <Button
              color="danger"
              variant="flat"
              onPress={() => setIsDeleteModalOpen(true)}
              startContent={<IconTrash size={16} />}
            >
              {t('list.actions.delete.label')}
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {t('details.sections.workloadInformation')}
        </h3>
      </div>

      <div className="columns-1 md:columns-2 xl:columns-3 gap-6 space-y-6">
        {/* Basic Information */}
        <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
          <CardHeader className="py-4 px-6 flex items-center">
            <h3 className="text-base font-semibold flex items-center space-x-2">
              <IconInfoCircle size={16} className="text-default-500" />
              <span>{t('details.sections.basicInformation')}</span>
            </h3>
          </CardHeader>
          <CardBody className="space-y-4 px-6 pb-6 pt-0">
            <div className="flex flex-col space-y-4">
              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.displayName.title')}
                  </h5>
                  <p className="text-sm">
                    {workload.displayName || workload.name}
                  </p>
                </div>
              </div>

              <div className="flex items-center">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.id.title')}
                  </h5>
                  <p className="font-mono text-sm">{workload.id}</p>
                </div>
              </div>

              <div className="flex items-center">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.type.title')}
                  </h5>
                  <ChipDisplay type={workload.type} variants={typeVariants} />
                </div>
              </div>

              <div className="flex items-center">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.status.title')}
                  </h5>
                  <StatusDisplay
                    type={workload.status}
                    variants={statusVariants}
                  />
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Resource Information */}
        <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
          <CardHeader className="py-4 px-6 flex items-center">
            <h3 className="text-base font-semibold flex items-center space-x-2">
              <IconServer size={16} className="text-default-500" />
              <span>{t('details.sections.resources')}</span>
            </h3>
          </CardHeader>
          <CardBody className="space-y-4 px-6 pb-6 pt-0">
            <div className="flex flex-col space-y-4">
              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.gpu.title')}
                  </h5>
                  {latestGpuDeviceUtilizationValue &&
                  latestGpuDeviceUtilizationValue > 0 ? (
                    <p className="text-sm">
                      {t('list.valueTemplates.gpu', {
                        value: latestGpuDeviceUtilizationValue,
                      })}
                    </p>
                  ) : (
                    <NoDataDisplay />
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.vram.title')}
                  </h5>
                  {latestGpuMemoryUtilizationValue &&
                  latestGpuMemoryUtilizationValue > 0 ? (
                    <p className="text-sm">
                      {t('list.valueTemplates.vram', {
                        value: displayMegabytesInGigabytes(
                          latestGpuMemoryUtilizationValue,
                        ),
                      })}
                    </p>
                  ) : (
                    <NoDataDisplay />
                  )}
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Timeline */}
        <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
          <CardHeader className="py-4 px-6 flex items-center">
            <h3 className="text-base font-semibold flex items-center space-x-2">
              <IconCalendar size={16} className="text-default-500" />
              <span>{t('details.sections.timeline')}</span>
            </h3>
          </CardHeader>
          <CardBody className="space-y-4 px-6 pb-6 pt-0">
            <div className="flex flex-col space-y-4">
              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.createdBy.title')}
                  </h5>
                  <p className="text-sm">{workload.createdBy}</p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.createdAt.title')}
                  </h5>
                  <DateDisplay date={workload.createdAt} />
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('details.fields.updatedAt')}
                  </h5>
                  <DateDisplay date={workload.updatedAt} />
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Model Information */}
        {(model || (isLoadingModel && workload?.modelId)) && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="py-4 px-6 flex items-center">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconDatabase size={16} className="text-default-500" />
                <span>{t('list.headers.model.title')}</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-4 px-6 pb-6 pt-0">
              {isLoadingModel ? (
                <div className="flex flex-col space-y-4">
                  <Skeleton className="w-full h-6 rounded-lg" />
                  <Skeleton className="w-3/4 h-6 rounded-lg" />
                  <Skeleton className="w-1/2 h-6 rounded-lg" />
                </div>
              ) : (
                <div className="flex flex-col space-y-4">
                  <div className="flex items-center space-x-3">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('list.headers.model.name')}
                      </h5>
                      <p className="text-sm">{model!.name}</p>
                    </div>
                  </div>

                  {model!.canonicalName && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.model.canonicalName')}
                        </h5>
                        <p className="font-mono text-sm">
                          {model!.canonicalName}
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center space-x-3">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('list.headers.model.id')}
                      </h5>
                      <p className="font-mono text-sm">{model!.id}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        )}

        {/* Dataset Information */}
        {(dataset || (isLoadingDataset && workload?.datasetId)) && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="py-4 px-6 flex items-center">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconDatabase size={16} className="text-default-500" />
                <span>{t('list.headers.dataset.title')}</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-4 px-6 pb-6 pt-0">
              {isLoadingDataset ? (
                <div className="flex flex-col space-y-4">
                  <Skeleton className="w-full h-6 rounded-lg" />
                  <Skeleton className="w-3/4 h-6 rounded-lg" />
                  <Skeleton className="w-1/2 h-6 rounded-lg" />
                </div>
              ) : (
                <div className="flex flex-col space-y-4">
                  <div className="flex items-center space-x-3">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('list.headers.dataset.name')}
                      </h5>
                      <p className="text-sm">{dataset!.name}</p>
                    </div>
                  </div>

                  {dataset!.description && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.dataset.description')}
                        </h5>
                        <p className="text-sm">{dataset!.description}</p>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center space-x-3">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('list.headers.dataset.id')}
                      </h5>
                      <p className="font-mono text-sm">{dataset!.id}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        )}

        {/* Chart Information */}
        {(chart || (isLoadingChart && workload?.chartId)) && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="py-4 px-6 flex items-center">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconDatabase size={16} className="text-default-500" />
                <span>{t('list.headers.chart.title')}</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-4 px-6 pb-6 pt-0">
              {isLoadingChart ? (
                <div className="flex flex-col space-y-4">
                  <Skeleton className="w-full h-6 rounded-lg" />
                  <Skeleton className="w-3/4 h-6 rounded-lg" />
                  <Skeleton className="w-1/2 h-6 rounded-lg" />
                </div>
              ) : (
                <div className="flex flex-col space-y-4">
                  <div className="flex items-center space-x-3">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('list.headers.chart.name')}
                      </h5>
                      <p className="text-sm">{chart!.name}</p>
                    </div>
                  </div>

                  {chart!.description && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.chart.description')}
                        </h5>
                        <p className="text-sm">{chart!.description}</p>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center space-x-3">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('list.headers.chart.id')}
                      </h5>
                      <p className="font-mono text-sm">{chart!.id}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        )}

        {/* Output Information */}
        {hasOutputData && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="py-4 px-6 flex items-center">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconWorld size={16} className="text-default-500" />
                <span>{t('details.sections.output')}</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-3 px-6 pb-6 pt-0">
              {workload.endpoints?.external && (
                <div className="space-y-2">
                  <h5 className="text-sm text-default-700">
                    {t('details.fields.externalHost')}
                  </h5>
                  <Input
                    value={getEndpointUrl(workload.endpoints.external)}
                    readOnly
                    variant="bordered"
                    classNames={{
                      input: 'font-mono text-sm',
                    }}
                    endContent={
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() =>
                          handleCopyToClipboard(
                            getEndpointUrl(workload.endpoints?.external || ''),
                            'externalHost',
                          )
                        }
                      >
                        {copiedField === 'externalHost' ? (
                          <IconCircleCheck size={16} className="text-success" />
                        ) : (
                          <IconCopy size={16} />
                        )}
                      </Button>
                    }
                  />
                </div>
              )}

              {workload.endpoints?.internal && (
                <div className="space-y-2">
                  <h5 className="text-sm text-default-700">
                    {t('details.fields.internalHost')}
                  </h5>
                  <Input
                    value={getEndpointUrl(workload.endpoints.internal)}
                    readOnly
                    variant="bordered"
                    classNames={{
                      input: 'font-mono text-sm',
                    }}
                    endContent={
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={() =>
                          handleCopyToClipboard(
                            getEndpointUrl(workload.endpoints?.internal || ''),
                            'internalHost',
                          )
                        }
                      >
                        {copiedField === 'internalHost' ? (
                          <IconCircleCheck size={16} className="text-success" />
                        ) : (
                          <IconCopy size={16} />
                        )}
                      </Button>
                    }
                  />
                </div>
              )}
            </CardBody>
          </Card>
        )}
      </div>

      {/* Modals */}
      <DeleteWorkloadModal
        isOpen={isDeleteModalOpen}
        onOpenChange={setIsDeleteModalOpen}
        workload={workload}
        onConfirmAction={deleteWorkloadMutation}
      />

      {isLogsModalOpen && (
        <WorkloadLogsModal
          isOpen={isLogsModalOpen}
          onOpenChange={setIsLogsModalOpen}
          workload={workload}
          namespace={activeProject!}
        />
      )}
    </div>
  );
};

export async function getServerSideProps(context: {
  req: any;
  res: any;
  locale: any;
  params: any;
  query: any;
}) {
  const { req, res, locale, params, query } = context;

  const session = await getServerSession(req, res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  const translations = await serverSideTranslations(locale, [
    'common',
    'workloads',
    'models',
  ]);

  let breadcrumb: { title: string; href?: string }[] = [
    {
      title:
        translations._nextI18Next?.initialI18nStore[locale]?.workloads?.details
          ?.breadcrumb || 'Workload details',
    },
  ];

  // Determine previous route from referer query param for correct parent breadcrumb
  const refererRoutePath = query?.ref || '/';
  const prevNavItem = aiWorkbenchMenuItems.find(
    (item) => item.href === refererRoutePath,
  );

  if (prevNavItem) {
    const title = get(
      translations._nextI18Next?.initialI18nStore[locale]?.common,
      prevNavItem.stringKey,
      prevNavItem.stringKey,
    );

    breadcrumb = [
      {
        title,
        href: prevNavItem.href,
      },
      ...breadcrumb,
    ];
  }

  return {
    props: {
      ...translations,
      pageBreadcrumb: breadcrumb,
    },
  };
}

export default WorkloadDetailsPage;
