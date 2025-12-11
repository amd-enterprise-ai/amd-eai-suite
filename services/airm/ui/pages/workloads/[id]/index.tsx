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
  IconCheck,
  IconInfoCircle,
  IconServer,
  IconCalendar,
  IconDatabase,
  IconWorld,
} from '@tabler/icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import { useState, useMemo } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import useSystemToast from '@/hooks/useSystemToast';

import { getWorkload, deleteWorkload } from '@/services/app/workloads';
import { getWorkload as getWorkloadServer } from '@/services/server/workloads';
import { getCluster } from '@/services/app/clusters';
import { getModel } from '@/services/app/models';
import { getDataset } from '@/services/app/datasets';
import { getChart } from '@/services/app/charts';
import { getAimById } from '@/services/app/aims';

import getWorkloadStatusVariants from '@/utils/app/workloads-status-variants';
import getWorkloadTypeVariants from '@/utils/app/workloads-type-variants';
import { authOptions } from '@/utils/server/auth';

import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import {
  StatusDisplay,
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
} from '@/components/shared/DataTable/CustomRenderers';
import { displayMegabytesInGigabytes } from '@/utils/app/memory';

import InferenceMetrics from '@/components/features/workloads/InferenceMetrics';

interface WorkloadDetailsPageProps {
  workload: Workload;
}

const WorkloadDetailsPage: React.FC<WorkloadDetailsPageProps> = ({
  workload: initialWorkload,
}) => {
  const { t } = useTranslation(['workloads', 'common']);
  const { toast } = useSystemToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id } = router.query;
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const { data: workload } = useQuery({
    queryKey: ['workload', id],
    queryFn: () => getWorkload(id as string, true),
    refetchInterval: 30000,
    initialData: initialWorkload,
  });

  const { data: cluster } = useQuery({
    queryKey: ['cluster', workload?.project?.clusterId],
    queryFn: () => getCluster(workload!.project.clusterId),
    enabled: !!workload?.project?.clusterId,
  });

  const { data: model, isLoading: isLoadingModel } = useQuery({
    queryKey: ['model', workload?.modelId],
    queryFn: () => getModel(workload!.modelId!, workload!.project.id),
    enabled: !!workload?.modelId && !!workload?.project?.id,
  });

  const { data: dataset, isLoading: isLoadingDataset } = useQuery({
    queryKey: ['dataset', workload?.datasetId],
    queryFn: () => getDataset(workload!.datasetId!, workload!.project.id),
    enabled: !!workload?.datasetId && !!workload?.project?.id,
    retry: false,
  });

  const { data: chart, isLoading: isLoadingChart } = useQuery({
    queryKey: ['chart', workload?.chartId],
    queryFn: () => getChart(workload!.chartId!),
    enabled: !!workload?.chartId,
  });

  const { data: aim, isLoading: isLoadingAim } = useQuery({
    queryKey: ['aim', workload?.aimId],
    queryFn: () => getAimById(workload!.aimId!, workload!.project.id),
    enabled: !!workload?.aimId && !!workload?.project?.id,
  });

  const canOpenWorkspace =
    workload?.type === WorkloadType.WORKSPACE &&
    workload?.status === WorkloadStatus.RUNNING &&
    (workload.output?.externalHost || workload.output?.host);

  const canOpenChat =
    workload?.type === WorkloadType.INFERENCE &&
    workload.status === WorkloadStatus.RUNNING;

  const canDelete = workload?.status !== WorkloadStatus.DELETED;

  const hasOutputData =
    workload?.output &&
    (workload.output.externalHost ||
      workload.output.internalHost ||
      workload.output.host);

  // For inference workloads, append the API endpoint path
  const isInferenceWorkload = workload?.type === WorkloadType.INFERENCE;

  const { mutate: deleteWorkloadMutation } = useMutation({
    mutationFn: deleteWorkload,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['workload', id],
      });
      toast.success(t('list.actions.delete.notification.success'));
      router.push('/workloads');
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

    const url = workload.output?.externalHost || workload.output?.host || '';
    window.open(url, '_blank');
  };

  const handleBack = () => {
    router.push('/workloads');
  };

  const handleOpenChat = () => {
    router.push(`/chat?workload=${workload?.id}`);
  };

  const getExternalHostUrl = (baseUrl: string) => {
    return isInferenceWorkload
      ? `${baseUrl}/v1/chat/completions`
      : baseUrl || '';
  };

  const getInternalHostUrl = (baseUrl: string) => {
    return isInferenceWorkload
      ? `http://${baseUrl}/v1/chat/completions`
      : baseUrl || '';
  };

  return (
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
          <div className="flex items-center space-x-3">
            <h2>{workload.displayName || workload.name}</h2>
            <StatusDisplay
              type={workload.status}
              variants={statusVariants}
              bypassProps={{ isShowBackground: true, isTextColored: true }}
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

      {/* Inference metrics */}
      {workload?.type === WorkloadType.INFERENCE &&
        workload?.aimId &&
        workload?.status === WorkloadStatus.RUNNING && (
          <InferenceMetrics workload={workload} />
        )}

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
                  {workload.allocatedResources?.gpuCount ? (
                    <p className="text-sm">
                      {t('list.valueTemplates.gpu', {
                        value: workload.allocatedResources.gpuCount,
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
                  {workload.allocatedResources?.vram ? (
                    <p className="text-sm">
                      {t('list.valueTemplates.vram', {
                        value: displayMegabytesInGigabytes(
                          workload.allocatedResources.vram,
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

        {/* Cluster Information */}
        <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
          <CardHeader className="py-4 px-6 flex items-center">
            <h3 className="text-base font-semibold flex items-center space-x-2">
              <IconServer size={16} className="text-default-500" />
              <span>{t('list.headers.cluster.title')}</span>
            </h3>
          </CardHeader>
          <CardBody className="space-y-4 px-6 pb-6 pt-0">
            <div className="flex flex-col space-y-4">
              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.cluster.name')}
                  </h5>
                  {cluster?.name ? (
                    <p className="text-sm">{cluster.name}</p>
                  ) : (
                    <NoDataDisplay />
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.cluster.id')}
                  </h5>
                  {workload.project?.clusterId ? (
                    <p className="font-mono text-sm">
                      {workload.project.clusterId}
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

        {/* AIM Information */}
        {(aim || (isLoadingAim && workload?.aimId)) && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="py-4 px-6 flex items-center">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconDatabase size={16} className="text-default-500" />
                <span>{t('list.headers.aim.title')}</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-4 px-6 pb-6 pt-0">
              {isLoadingAim ? (
                <div className="flex flex-col space-y-4">
                  <Skeleton className="w-full h-6 rounded-lg" />
                  <Skeleton className="w-3/4 h-6 rounded-lg" />
                  <Skeleton className="w-2/3 h-6 rounded-lg" />
                  <Skeleton className="w-1/2 h-6 rounded-lg" />
                </div>
              ) : (
                <div className="flex flex-col space-y-4">
                  {aim!.imageName && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.aim.image')}
                        </h5>
                        <p className="font-mono text-sm">{aim!.imageName}</p>
                      </div>
                    </div>
                  )}

                  {aim!.imageTag && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.aim.imageTag')}
                        </h5>
                        <p className="font-mono text-sm">{aim!.imageTag}</p>
                      </div>
                    </div>
                  )}

                  {aim!.canonicalName && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.aim.canonicalName')}
                        </h5>
                        <p className="font-mono text-sm">
                          {aim!.canonicalName}
                        </p>
                      </div>
                    </div>
                  )}

                  {aim!.description?.short && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.aim.description')}
                        </h5>
                        <p className="text-sm">{aim!.description.short}</p>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center space-x-3">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('list.headers.aim.id')}
                      </h5>
                      <p className="font-mono text-sm">{aim!.id}</p>
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
              {workload.output?.externalHost && (
                <div className="space-y-2">
                  <h5 className="text-sm text-default-700">
                    {t('details.fields.externalHost')}
                  </h5>
                  <Input
                    value={getExternalHostUrl(workload.output.externalHost)}
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
                            getExternalHostUrl(
                              workload.output?.externalHost || '',
                            ),
                            'externalHost',
                          )
                        }
                      >
                        {copiedField === 'externalHost' ? (
                          <IconCheck size={16} className="text-success" />
                        ) : (
                          <IconCopy size={16} />
                        )}
                      </Button>
                    }
                  />
                </div>
              )}

              {workload.output?.internalHost && (
                <div className="space-y-2">
                  <h5 className="text-sm text-default-700">
                    {t('details.fields.internalHost')}
                  </h5>
                  <Input
                    value={getInternalHostUrl(workload.output.internalHost)}
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
                            getInternalHostUrl(
                              workload.output?.internalHost || '',
                            ),
                            'internalHost',
                          )
                        }
                      >
                        {copiedField === 'internalHost' ? (
                          <IconCheck size={16} className="text-success" />
                        ) : (
                          <IconCopy size={16} />
                        )}
                      </Button>
                    }
                  />
                </div>
              )}

              {workload.output?.host && (
                <div className="space-y-2">
                  <h5 className="text-sm text-default-700">
                    {t('details.fields.host')}
                  </h5>
                  <Input
                    value={workload.output.host}
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
                            workload.output?.host || '',
                            'host',
                          )
                        }
                      >
                        {copiedField === 'host' ? (
                          <IconCheck size={16} className="text-success" />
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
}) {
  const { req, res, locale, params } = context;

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

  try {
    const workload = await getWorkloadServer({
      workloadId: params.id,
      accessToken: session.accessToken as string,
      withResources: true,
    });

    const translations = await serverSideTranslations(locale, [
      'common',
      'workloads',
      'models',
    ]);

    const breadcrumb = [
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.workloads
            ?.title || 'Workloads',
        href: '/workloads',
      },
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.workloads
            ?.details?.breadcrumb || 'Details',
      },
    ];

    return {
      props: {
        ...translations,
        workload,
        pageBreadcrumb: breadcrumb,
      },
    };
  } catch (error) {
    console.error('Workload not found: ' + error);
    return {
      redirect: {
        destination: '/workloads',
        permanent: false,
      },
    };
  }
}

export default WorkloadDetailsPage;
