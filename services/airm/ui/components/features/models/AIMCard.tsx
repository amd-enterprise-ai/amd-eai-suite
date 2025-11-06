// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';
import { Card, CardFooter, CardHeader, Chip, Divider } from '@heroui/react';

import { Aim } from '@/types/aims';
import { useTranslation } from 'next-i18next';

import { ModelIcon } from '@/components/shared/ModelIcons';
import ThreeDotActionsDropdown from '@/components/shared/Dropdown/ThreeDotActionsDropdown';
import {
  isDeployed,
  isDeploying,
  isUndeploying,
  isNotDeployed,
  isDeploymentFailed,
} from '@/utils/app/workload-deployment-status';

import { IconCheck, IconLock } from '@tabler/icons-react';

import { IconLoaderQuarter } from '@tabler/icons-react';

interface Props {
  item: Aim;
  onDeploy: (aim: Aim) => void;
  onUndeploy: (aim: Aim) => void;
  onConnect: (aim: Aim) => void;
}

export const AIMCard = ({ item, onDeploy, onUndeploy, onConnect }: Props) => {
  const workload = item.workload;
  const { t } = useTranslation('models', { keyPrefix: 'aimCatalog' });
  const cardActions = useMemo(() => {
    const actions = [];

    if ((isNotDeployed(workload) || isDeploymentFailed(workload)) && onDeploy) {
      actions.push({
        key: 'deploy',
        label: t('actions.deploy.label'),
        onPress: () => onDeploy(item),
      });
    }

    if (isDeployed(workload)) {
      actions.push({
        key: 'connect',
        label: t('actions.connect.label'),
        onPress: () => onConnect(item),
      });
    }

    if (isDeployed(workload) && onUndeploy) {
      actions.push({
        key: 'undeploy',
        label: t('actions.undeploy.label'),
        onPress: () => onUndeploy(item),
      });
    }

    return actions;
  }, [workload, t, item, onDeploy, onUndeploy, onConnect]);

  return (
    <Card
      className="max-w-[420px] min-w-[380px] flex-1 dark:bg-default-100/50 p-1"
      key={item.id}
      shadow="sm"
      radius="md"
      classNames={{
        header: `flex items-center justify-between`,
        footer: `flex flex-nowrap gap-2 justify-between items-start`,
      }}
    >
      <CardHeader>
        <div className="flex gap-4 h-full">
          <div className="w-12 h-12">
            <ModelIcon iconName={item.canonicalName} width={48} height={48} />
          </div>
          <div className="flex items-start flex-col  gap-1">
            <div className="text-md font-semibold flex flex-row gap-2">
              {item.title}
              {isDeployed(workload) && (
                <Chip
                  size="sm"
                  color="success"
                  variant="light"
                  startContent={<IconCheck size={12} />}
                >
                  {t('status.deployed')}
                </Chip>
              )}
              {isDeploying(workload) && (
                <Chip
                  size="sm"
                  color="default"
                  variant="light"
                  startContent={
                    <IconLoaderQuarter className="animate-spin" size={12} />
                  }
                  classNames={{ base: 'text-foreground/60' }}
                >
                  {t('status.deploying')}
                </Chip>
              )}
              {isUndeploying(workload) && (
                <Chip
                  size="sm"
                  color="default"
                  variant="light"
                  startContent={
                    <IconLoaderQuarter className="animate-spin" size={12} />
                  }
                  classNames={{ base: 'text-foreground/60' }}
                >
                  {t('status.undeploying')}
                </Chip>
              )}
            </div>
            <div className="text-sm text-foreground/40">{item.imageTag}</div>
            <div className="text-sm text-foreground/60">
              {item.description.short}
            </div>
          </div>
        </div>
      </CardHeader>
      <Divider />
      <CardFooter>
        <div className="flex flex-wrap gap-1">
          {item.isHfTokenRequired && (
            <Chip variant="flat" color="default" size="sm">
              <IconLock size={12} />
            </Chip>
          )}
          {item.isPreview && (
            <Chip variant="flat" color="warning" size="sm">
              Preview
            </Chip>
          )}
          {item.tags?.map((tag) => (
            <Chip key={tag} variant="bordered" size="sm">
              {tag}
            </Chip>
          ))}
        </div>
        <div className="flex gap-2">
          <ThreeDotActionsDropdown actions={cardActions} item={item} />
        </div>
      </CardFooter>
    </Card>
  );
};

AIMCard.displayName = 'AIMCard';
