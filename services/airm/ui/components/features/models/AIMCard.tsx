// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo, useState, useRef, useEffect } from 'react';
import {
  Card,
  CardFooter,
  CardHeader,
  Chip,
  Divider,
  Tooltip,
} from '@heroui/react';

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

import Status, { Intent } from '@/components/shared/Status/Status';

interface Props {
  item: Aim;
  onDeploy: (aim: Aim) => void;
  onUndeploy: (aim: Aim) => void;
  onConnect: (aim: Aim) => void;
}

export const AIMCard = ({ item, onDeploy, onUndeploy, onConnect }: Props) => {
  const workload = item.workload;
  const { t } = useTranslation('models', { keyPrefix: 'aimCatalog' });
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [isDescriptionLong, setIsDescriptionLong] = useState(false);
  const descriptionRef = useRef<HTMLDivElement>(null);

  // CSS-based overflow detection: check if content overflows when clamped to 3 lines
  useEffect(() => {
    const checkOverflow = () => {
      if (!descriptionRef.current) return;

      const element = descriptionRef.current;
      const isClamped = element.classList.contains('line-clamp-3');

      if (isClamped) {
        // When clamped, compare scrollHeight to clientHeight
        // If scrollHeight > clientHeight, content overflows
        setIsDescriptionLong(element.scrollHeight > element.clientHeight);
      } else {
        // When expanded, temporarily apply clamp to check if it would overflow
        element.classList.add('line-clamp-3');
        const wouldOverflow = element.scrollHeight > element.clientHeight;
        element.classList.remove('line-clamp-3');
        setIsDescriptionLong(wouldOverflow);
      }
    };

    // Re-check when card size changes (observe parent container for width changes)
    const resizeObserver = new ResizeObserver(() => {
      checkOverflow();
    });

    // Use requestAnimationFrame to ensure layout is complete
    const frameId = requestAnimationFrame(() => {
      checkOverflow();
      if (descriptionRef.current?.parentElement) {
        resizeObserver.observe(descriptionRef.current.parentElement);
      }
    });

    return () => {
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
    };
  }, [item.description.short, isDescriptionExpanded]);

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
      className="flex-1 dark:bg-default-100/50 p-1 grid grid-cols-1 grid-rows-[1fr_auto_auto]"
      key={item.id}
      shadow="sm"
      radius="md"
      classNames={{
        header: `flex items-center justify-between min-h-0`,
        footer: `flex flex-nowrap gap-2 justify-between items-start`,
      }}
    >
      <CardHeader>
        <div className="flex gap-4 h-full">
          <div className="w-12 h-12">
            <ModelIcon iconName={item.canonicalName} width={48} height={48} />
          </div>
          <div className="flex items-start flex-col  gap-1">
            <div className="text-md font-semibold flex flex-row gap-2 leading-tight">
              {item.title}
              {isDeployed(workload) && (
                <Status
                  label={t('status.deployed')}
                  color="success"
                  icon={IconCheck}
                  size="sm"
                  isTextColored
                />
              )}
              {isDeploying(workload) && (
                <Status
                  label={t('status.deploying')}
                  intent={Intent.PENDING}
                  color="default"
                  size="sm"
                  isSubtle
                />
              )}
              {isUndeploying(workload) && (
                <Status
                  label={t('status.undeploying')}
                  intent={Intent.PENDING}
                  color="default"
                  size="sm"
                  isSubtle
                />
              )}
            </div>
            <div className="text-sm text-foreground/40">{item.imageTag}</div>
            <p
              ref={descriptionRef}
              className={`text-sm transition-colors ${
                isDescriptionExpanded ? '' : 'line-clamp-3'
              } ${
                isDescriptionLong
                  ? 'cursor-pointer hover:text-foreground/80'
                  : ''
              }`}
              onClick={
                isDescriptionLong
                  ? () => setIsDescriptionExpanded(!isDescriptionExpanded)
                  : undefined
              }
              role={isDescriptionLong ? 'button' : undefined}
              tabIndex={isDescriptionLong ? 0 : undefined}
              aria-expanded={
                isDescriptionLong ? isDescriptionExpanded : undefined
              }
              onKeyDown={
                isDescriptionLong
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === 'Space') {
                        e.preventDefault();
                        setIsDescriptionExpanded(!isDescriptionExpanded);
                      }
                    }
                  : undefined
              }
            >
              {item.description.short}
            </p>
          </div>
        </div>
      </CardHeader>

      <Divider />
      <CardFooter className="flex flex-col">
        <div className="flex flex-row justify-between w-full">
          <div className="flex flex-wrap gap-1">
            {item.isHfTokenRequired && (
              <Tooltip content={t('tooltips.hfTokenRequired')}>
                <Chip variant="flat" color="default" size="sm">
                  <IconLock size={12} />
                </Chip>
              </Tooltip>
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
        </div>
      </CardFooter>
    </Card>
  );
};

AIMCard.displayName = 'AIMCard';
