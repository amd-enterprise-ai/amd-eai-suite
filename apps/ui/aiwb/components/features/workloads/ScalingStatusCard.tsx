// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Displays the current scaling status of a deployed AIMService.
 * When autoscaling is disabled (minReplicas === maxReplicas === 1),
 * this card should be hidden and "Autoscaling Disabled" shown in Resources card.
 */

import { Card, CardBody, CardHeader, Button } from '@heroui/react';
import { IconArrowsMaximize, IconSettings } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'next-i18next';
import { AIMServiceSpec, AIMServiceRuntime } from '@/types/aims';
import { SCALING_METRIC_KEYS } from '@/lib/app/aims';
import { DeploymentSettingsDrawer } from './DeploymentSettingsDrawer';

interface Props {
  /** The AIMService spec containing scaling configuration */
  spec: AIMServiceSpec;
  /** Runtime scaling status from the CRD status.runtime */
  runtime?: AIMServiceRuntime;
  /** Namespace (project) where the workload is deployed */
  namespace?: string;
  /** Workload ID for the settings drawer */
  id?: string;
  /** Called after autoscaling settings are saved successfully */
  onSettingsSaved?: () => void;
}

export const ScalingStatusCard = ({
  spec,
  runtime,
  namespace,
  id,
  onSettingsSaved,
}: Props) => {
  const { t } = useTranslation('autoscaling');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Extract scaling info from spec
  const firstMetric = spec.autoScaling?.metrics?.[0]?.podmetric;
  const metricQuery = firstMetric?.metric?.query || '';

  // Get translated label for metric query
  const metric = SCALING_METRIC_KEYS.find((m) => m.key === metricQuery);
  const metricLabel = metric
    ? t(`scalingMetric.options.${metric.translationKey}`)
    : metricQuery;

  const operationOverTime = firstMetric?.metric?.operationOverTime || 'avg';
  const targetValue = firstMetric?.target?.value
    ? parseInt(firstMetric.target.value, 10)
    : 0;
  const targetType = firstMetric?.target?.type || 'Value';

  // Drawer initial values
  const drawerInitialValues = {
    minReplicas: spec.minReplicas ?? 1,
    maxReplicas: spec.maxReplicas ?? 3,
    metricQuery,
    operationOverTime,
    targetType,
    targetValue,
  };

  return (
    <>
      <Card
        data-testid="scaling-status-card"
        className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm"
      >
        <CardHeader className="py-4 px-6 flex items-center justify-between">
          <h3 className="text-base font-semibold flex items-center space-x-2">
            <IconArrowsMaximize size={16} className="text-default-500" />
            <span>{t('title')}</span>
          </h3>
          <Button
            data-testid="scaling-settings-button"
            size="sm"
            variant="light"
            startContent={<IconSettings size={14} />}
            onPress={() => setIsDrawerOpen(true)}
          >
            {t('actions.settings')}
          </Button>
        </CardHeader>

        <CardBody className="px-6 pb-6 pt-0 space-y-3">
          {/* Current Replicas Display: current / desired Replicas (min) */}
          {runtime?.currentReplicas != null && (
            <>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-foreground">
                  {runtime.currentReplicas}
                </span>
                <span className="text-base text-default-500">
                  / {runtime.maxReplicas ?? '–'}
                </span>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-base text-default-500 ml-0">
                  {t('replicasMinimum', { count: spec.minReplicas ?? 1 })}
                </span>
              </div>
            </>
          )}

          {/* Scaling Metric and Target - same row */}
          <div className="flex items-start justify-between">
            <div>
              <div className="text-small text-default-500">
                {t('scalingMetric.label')}
              </div>
              <div className="text-small font-medium text-foreground">
                {metricLabel}
              </div>
            </div>
            <div className="text-right">
              <div className="text-small text-default-500">
                {t('targetValue.label')}
              </div>
              <div className="text-small font-medium text-foreground">
                {targetValue} ({operationOverTime})
              </div>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Autoscaling Settings Drawer */}
      <DeploymentSettingsDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onSuccess={onSettingsSaved}
        namespace={namespace}
        id={id}
        initialValues={drawerInitialValues}
      />
    </>
  );
};

export default ScalingStatusCard;
