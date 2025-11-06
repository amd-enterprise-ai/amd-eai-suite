// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody, CardHeader, Button, Input } from '@heroui/react';
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

import getWorkloadStatusVariants from '@/utils/app/workloads-status-variants';
import getWorkloadTypeVariants from '@/utils/app/workloads-type-variants';
import { authOptions } from '@/utils/server/auth';

import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import {
  StatusBadgeDisplay,
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
} from '@/components/shared/DataTable/CustomRenderers';
import StatusHeaderDisplay from '@/components/shared/ChipsAndStatus/StatusHeaderDisplay';
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
    queryFn: () => getCluster(workload!.project!.clusterId),
    enabled: !!workload?.project?.clusterId,
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
            <StatusHeaderDisplay
              type={workload.status}
              variants={statusVariants}
            />
            <h2>{workload.displayName || workload.name}</h2>
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
                    {t('list.headers.chartId.title')}
                  </h5>
                  <p className="font-mono text-sm">{workload.chartId}</p>
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
                  <StatusBadgeDisplay
                    type={workload.status}
                    variants={statusVariants}
                  />
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Cluster and Resource Information */}
        <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
          <CardHeader className="py-4 px-6 flex items-center">
            <h3 className="text-base font-semibold flex items-center space-x-2">
              <IconServer size={16} className="text-default-500" />
              <span>{t('details.sections.clusterAndResources')}</span>
            </h3>
          </CardHeader>
          <CardBody className="space-y-4 px-6 pb-6 pt-0">
            <div className="flex flex-col space-y-4">
              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.clusterName.title')}
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
                    {t('list.headers.clusterId.title')}
                  </h5>
                  {cluster?.id ? (
                    <p className="font-mono text-sm">{cluster.id}</p>
                  ) : (
                    <NoDataDisplay />
                  )}
                </div>
              </div>
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

        {/* Model and Dataset Information */}
        {(workload.model || workload.dataset) && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="py-4 px-6 flex items-center">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconDatabase size={16} className="text-default-500" />
                <span>{t('details.sections.modelAndDataset')}</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-4 px-6 pb-6 pt-0">
              <div className="flex flex-col space-y-4">
                {workload.model && (
                  <>
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.modelName.title')}
                        </h5>
                        <p className="text-sm">{workload.model.name}</p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.modelId.title')}
                        </h5>
                        <p className="font-mono text-sm">{workload.modelId}</p>
                      </div>
                    </div>
                  </>
                )}

                {workload.dataset && (
                  <>
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.datasetName.title')}
                        </h5>
                        <p className="text-sm">{workload.dataset.name}</p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.datasetId.title')}
                        </h5>
                        <p className="font-mono text-sm">
                          {workload.datasetId}
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>
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
