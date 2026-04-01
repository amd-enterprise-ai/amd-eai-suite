// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { useProject } from '@/contexts/ProjectContext';

import { authOptions } from '@amdenterpriseai/utils/server';

import { ChatView } from '@/components/features/chat/ChatView';
import { RelevantDocs } from '@amdenterpriseai/components';
import { listChattableWorkloads } from '@/lib/app/chat';

const ChatPage = () => {
  const { toast } = useSystemToast();
  const { t } = useTranslation('chat');
  const { activeProject } = useProject();

  // Load chattable workloads using optimized endpoint
  const { data: chattableData, error: workloadsError } = useQuery({
    queryKey: ['workloads', activeProject, 'chattable'],
    queryFn: () => listChattableWorkloads(activeProject!),
    enabled: !!activeProject,
  });

  const workloads = chattableData?.workloads ?? [];
  const workloadDisplayInfo = chattableData?.workloadDisplayInfo ?? {};

  // Handle workloads loading error
  useEffect(() => {
    if (workloadsError) {
      toast.error(t('errors.workloadLoadingFailed'));
    }
  }, [workloadsError, toast, t]);

  return (
    <div className="flex flex-col flex-1 h-full w-full">
      <div className="flex flex-1 h-full w-full">
        <ChatView
          workloads={workloads}
          workloadDisplayInfo={workloadDisplayInfo}
        />
      </div>
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
      ...(await serverSideTranslations(locale, [
        'common',
        'chat',
        'models',
        'sharedComponents',
      ])),
    },
  };
}
export default ChatPage;
