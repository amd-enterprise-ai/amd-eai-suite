// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import useSystemToast from '@/hooks/useSystemToast';

import { listWorkloads } from '@/services/app/workloads';
import { useProject } from '@/contexts/ProjectContext';

import { authOptions } from '@/utils/server/auth';

import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';

import { ChatView } from '@/components/features/chat/ChatView';
import { getAims } from '@/services/app/aims';
import { Aim } from '@/types/aims';

const ChatPage = () => {
  const { toast } = useSystemToast();
  const { t } = useTranslation('chat');
  const { activeProject } = useProject();

  // Load workloads using React Query
  const { data: workloads = [], error: workloadsError } = useQuery({
    queryKey: ['workloads', activeProject],
    queryFn: async () => {
      const workloads = await listWorkloads(activeProject!, {
        type: [WorkloadType.INFERENCE],
        status: [WorkloadStatus.RUNNING],
      });

      return workloads;
    },
    enabled: !!activeProject,
  });

  const { data: aims, error: aimsError } = useQuery<Aim[]>({
    queryKey: ['project', activeProject, 'aim-catalog'],
    queryFn: () => getAims(activeProject!),
    enabled: !!activeProject,
  });

  const chatWorkloads = useMemo(() => {
    const workloadsFromAims = workloads.filter((workload) => {
      const associatedAim = aims?.find(
        (aim) => aim.canonicalName === workload.userInputs?.canonicalName,
      );
      return associatedAim && associatedAim.tags.includes('chat');
    });

    const includedWorkloadIds = new Set(workloadsFromAims.map((w) => w.id));

    // TODO: deprecated, remove after all models have been migrated to AIMs
    const workloadsFromCharts = workloads.filter(
      (workload) =>
        workload.capabilities?.includes('chat') &&
        !includedWorkloadIds.has(workload.id),
    );

    return [...workloadsFromAims, ...workloadsFromCharts];
  }, [workloads, aims]);

  // Handle workloads or aims loading error
  useEffect(() => {
    if (aimsError || workloadsError) {
      toast.error(t('errors.workloadLoadingFailed'));
    }
  }, [aimsError, workloadsError, toast, t]);

  return (
    <div className="flex flex-1 h-full w-full">
      <ChatView workloads={chatWorkloads} />
    </div>
  );
};

export async function getServerSideProps(context: {
  req: any;
  res: any;
  locale: any;
}) {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

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

  return {
    props: {
      ...(await serverSideTranslations(locale, ['common', 'chat'])),
    },
  };
}
export default ChatPage;
