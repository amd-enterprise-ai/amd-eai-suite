// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useState, useRef, useEffect, useMemo } from 'react';
import {
  Card,
  CardFooter,
  CardHeader,
  Divider,
  Link,
  Tooltip,
  ButtonGroup,
} from '@heroui/react';

import { useTranslation } from 'next-i18next';
import { ActionButton, Alert } from '@amdenterpriseai/components';
import { ModelIcon } from '@/components/shared/ModelIcons';
import { TruncatedTagsRow } from '@/components/shared/TruncatedTagsRow';
import { NestedDropdown, DropdownItem } from '@amdenterpriseai/components';
import {
  IconAlertTriangle,
  IconChevronDown,
  IconLock,
} from '@tabler/icons-react';
import {
  AggregatedAIM,
  AIMService,
  AIMServiceStatus,
  AIMMetric,
  AIMWorkloadStatus,
  ParsedAIM,
} from '@/types/aims';
import { Intent } from '@amdenterpriseai/types';
import { Status } from '@amdenterpriseai/components';

interface Props {
  aggregatedAim: AggregatedAIM;
  onDeploy: () => void;
  onOpenDetails: (serviceId: string) => void;
  onChatWithModel: (serviceId: string) => void;
  onConnectToModel: (aim: ParsedAIM) => void;
  onUndeploy: (
    namespace: string,
    serviceId: string,
    displayName: string,
  ) => void;
}

export const AIMCard = ({
  aggregatedAim,
  onDeploy,
  onOpenDetails,
  onChatWithModel,
  onConnectToModel,
  onUndeploy,
}: Props) => {
  const tags = aggregatedAim.aggregated.tags ?? [];
  const { t } = useTranslation(['models']);
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
  }, [aggregatedAim.aggregated.description.short, isDescriptionExpanded]);

  const allDeployments = useMemo(() => {
    const deployments: Array<{
      service: AIMService;
      imageVersion: string;
      parsedAim: ParsedAIM;
    }> = [];

    aggregatedAim.parsedAIMs.forEach((version) => {
      version.deployedServices?.forEach((service) => {
        // Only include services with a valid id
        if (service.id) {
          deployments.push({
            service,
            imageVersion: version.imageVersion,
            parsedAim: version,
          });
        }
      });
    });

    return deployments;
  }, [aggregatedAim.parsedAIMs]);

  const getDeploymentStatusIntent = (status: AIMServiceStatus): Intent => {
    if (status === AIMServiceStatus.RUNNING) {
      return Intent.SUCCESS;
    }
    if (
      status === AIMServiceStatus.PENDING ||
      status === AIMServiceStatus.STARTING
    ) {
      return Intent.PENDING;
    }
    return Intent.WARNING;
  };

  const cardActions = useMemo(() => {
    const actions: DropdownItem[] = [];

    if (allDeployments.length > 0) {
      const deploymentActions: DropdownItem[] = [];

      allDeployments.forEach(({ service, imageVersion, parsedAim }) => {
        const serviceId = service.id as string;
        const metricKey =
          (service.spec.overrides?.metric as string | undefined) ||
          AIMMetric.Default;
        const metricLabel = t(`performanceMetrics.values.${metricKey}`);
        const deploymentInfo = [imageVersion, metricLabel]
          .filter(Boolean)
          .join(' • ');

        const isRunning = service.status.status === AIMServiceStatus.RUNNING;

        // Create nested actions for each deployment
        const nestedActions: DropdownItem[] = [
          {
            key: `open-details-${serviceId}`,
            label: t('aimCatalog.actions.workloadDetails.label'),
            onPress: () => onOpenDetails(serviceId),
          },
        ];

        if (isRunning) {
          nestedActions.push({
            key: `chat-${serviceId}`,
            label: t('aimCatalog.actions.chatWithModel.label'),
            onPress: () => onChatWithModel(serviceId),
          });
          nestedActions.push({
            key: `connect-${serviceId}`,
            label: t('aimCatalog.actions.connect.label'),
            onPress: () =>
              onConnectToModel({
                ...parsedAim,
                deployedService: service,
                deployedServices: [service],
              }),
          });
        }

        nestedActions.push({
          key: `undeploy-${serviceId}`,
          label: t('aimCatalog.actions.undeploy.label'),
          color: 'danger',
          onPress: () =>
            onUndeploy(
              service.metadata.namespace,
              serviceId,
              service.metadata.name,
            ),
        });

        // Add deployment as parent item with nested actions
        deploymentActions.push({
          key: `deployment-${serviceId}`,
          label: service.metadata.name,
          description: deploymentInfo,
          onPress: () => {},
          actions: nestedActions,
          startContent: (
            <Status
              intent={getDeploymentStatusIntent(service.status.status)}
              size="md"
            />
          ),
        });
      });

      actions.push({
        key: 'deployments',
        label: t('aimCatalog.card.deploymentsCount', {
          count: allDeployments.length,
        }),
        onPress: () => {},
        actions: deploymentActions,
        isSection: true,
      });
    }

    return actions;
  }, [
    aggregatedAim.parsedAIMs,
    onDeploy,
    allDeployments,
    onOpenDetails,
    onChatWithModel,
    onConnectToModel,
    onUndeploy,
    t,
  ]);

  const isSupported = aggregatedAim.isSupported;

  return (
    <Card
      className={`flex-1 dark:bg-default-100/50 p-1 grid grid-cols-1 ${
        isSupported
          ? 'grid-rows-[1fr_auto_auto]'
          : 'grid-rows-[auto_1fr_auto_auto]'
      }`}
      shadow="sm"
      radius="md"
      classNames={{
        header: `flex items-center justify-between min-h-0`,
        footer: `flex flex-nowrap gap-2 justify-between items-start`,
      }}
    >
      {!isSupported && (
        <div
          data-testid="unsupported-banner"
          role="alert"
          className="-mx-1 -mt-1"
        >
          <Alert
            color="danger"
            variant="flat"
            hideIconWrapper={true}
            icon={
              <span className="text-sm font-bold text-danger dark:text-danger-400">
                <IconAlertTriangle />
              </span>
            }
            classNames={{
              base: 'rounded-t-md rounded-bl-none rounded-br-none bg-danger/20 dark:bg-danger/30 border-b border-danger px-0.5 py-0.5 text-danger dark:text-danger-400',
              description: 'text-xs text-inherit',
            }}
            description={
              <>
                {t('aimCatalog.unsupported.message')}{' '}
                <Link
                  href={t('aimCatalog.unsupported.linkUrl', {
                    canonicalName: aggregatedAim.aggregated.canonicalName,
                  })}
                  isExternal
                  showAnchorIcon={false}
                  className="text-inherit text-xs font-bold hover:opacity-60"
                >
                  {t('aimCatalog.unsupported.linkText')}
                </Link>
                .
              </>
            }
          />
        </div>
      )}

      <CardHeader>
        <div
          className={`flex gap-4 h-full ${!isSupported ? 'opacity-50' : ''}`}
        >
          <div className="flex items-start flex-col gap-1 w-full">
            <div className="flex flex-row gap-2 items-start w-full">
              <div className="mb-1">
                <ModelIcon
                  iconName={aggregatedAim.aggregated.canonicalName}
                  width={48}
                  height={48}
                />
              </div>
              <div className="ml-auto">
                {aggregatedAim.deploymentCounts[AIMWorkloadStatus.PENDING] >
                  0 && (
                  <Status
                    label={t('aimCatalog.status.deploying')}
                    intent={Intent.PENDING}
                    size="sm"
                    isTextColored
                  />
                )}
              </div>
            </div>
            <div className="text-md font-semibold leading-tight w-full">
              {aggregatedAim.aggregated.title}
            </div>
            <div className="flex flex-row gap-1 text-sm text-foreground/60">
              <span>{aggregatedAim.aggregated.aiLabName}</span>
              <span>&bull;</span>
              <span>
                {t('aimCatalog.card.versionCount', {
                  count: aggregatedAim.parsedAIMs.length,
                })}
              </span>
              {aggregatedAim.aggregated.isHfTokenRequired && (
                <>
                  <span>&bull;</span>
                  <Tooltip
                    content={t('aimCatalog.tooltips.hfTokenRequired')}
                    delay={300}
                  >
                    <span className="inline-flex flex-row gap-1 items-center cursor-help">
                      <IconLock size={12} /> {t('aimCatalog.card.gated')}
                    </span>
                  </Tooltip>
                </>
              )}
            </div>
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
              {aggregatedAim.aggregated.description.short}
            </p>
          </div>
        </div>
      </CardHeader>

      <Divider />
      <CardFooter className="flex flex-col">
        <div className="flex flex-row justify-between items-center w-full">
          <TruncatedTagsRow
            tags={tags}
            formatMoreCount={(count) =>
              t('aimCatalog.card.tagsMoreCount', { count })
            }
            className={!isSupported ? 'opacity-50' : ''}
          />

          {isSupported && (
            <ButtonGroup>
              <ActionButton
                primary
                color="primary"
                size="sm"
                onPress={() => onDeploy()}
              >
                {t('aimCatalog.actions.deploy.label')}
              </ActionButton>
              {allDeployments.length > 0 ? (
                <NestedDropdown actions={cardActions}>
                  <ActionButton
                    primary
                    color="primary"
                    size="sm"
                    aria-label={t('aimCatalog.card.actionsMenu')}
                    icon={<IconChevronDown size={16} />}
                    isDisabled={
                      aggregatedAim.deploymentCounts[
                        AIMWorkloadStatus.PENDING
                      ] === 0 &&
                      aggregatedAim.deploymentCounts[
                        AIMWorkloadStatus.DEPLOYED
                      ] === 0
                    }
                  />
                </NestedDropdown>
              ) : (
                <ActionButton
                  primary
                  color="primary"
                  size="sm"
                  aria-label={t('aimCatalog.card.actionsMenu')}
                  icon={<IconChevronDown size={16} />}
                  isDisabled
                />
              )}
            </ButtonGroup>
          )}
        </div>
      </CardFooter>
    </Card>
  );
};

AIMCard.displayName = 'AIMCard';
