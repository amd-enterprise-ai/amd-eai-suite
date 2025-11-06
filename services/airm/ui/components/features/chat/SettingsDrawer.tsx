// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Checkbox,
  Divider,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerHeader,
  Slider,
} from '@heroui/react';
import React from 'react';

import { useTranslation } from 'next-i18next';
import { InferenceSettings } from '@/types/models';
import { Workload } from '@/types/workloads';

import { InputWrapper } from '@/components/shared/Input/InputWrapper';
import TextAreaWrapper from '@/components/shared/Textarea/TextAreaWrapper';

interface Props {
  showSyncSettings: boolean;
  settings: InferenceSettings;
  onSettingsChange: (settings: InferenceSettings) => void;
  syncSettings: boolean;
  onSyncSettingsChange: (syncSettings: boolean) => void;
  selectedModelWorkload: Workload | undefined;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

const SettingsDrawer: React.FC<Props> = ({
  settings,
  onSettingsChange,
  showSyncSettings,
  syncSettings,
  onSyncSettingsChange,
  selectedModelWorkload,
  isOpen,
  onOpenChange,
}) => {
  const { t } = useTranslation('chat');

  return (
    <Drawer isOpen={isOpen} onOpenChange={onOpenChange} radius="none" size="sm">
      <DrawerContent>
        <DrawerHeader>
          <div className="flex items-center justify-between">
            <div className="text-lg font-semibold">
              <h3>{t('modelSettings.title')}</h3>
              <div className="text-default-500 max-w-80 text-sm font-light text-nowrap truncate">
                {selectedModelWorkload?.displayName}
              </div>
            </div>
          </div>
        </DrawerHeader>
        <Divider />
        <DrawerBody className="overflow-y-scroll max-h-[600px] p-6">
          <div className="w-full">
            {showSyncSettings && (
              <div className="flex justify-between items-center border-b pb-4 mb-4 dark:border-default-100">
                <span className="text-sm text-default-600 dark:text-default-500">
                  {t('modelSettings.syncSettings.description')}
                </span>
                <Checkbox
                  isSelected={syncSettings}
                  onChange={(e) => onSyncSettingsChange(e.target.checked)}
                >
                  {t('modelSettings.syncSettings.label')}
                </Checkbox>
              </div>
            )}

            <InputWrapper
              label={t('modelSettings.temperature.label') ?? ''}
              value={settings.temperature}
              description={t('modelSettings.temperature.description') ?? ''}
              tooltip={t('modelSettings.temperature.tooltip') ?? ''}
            >
              <Slider
                aria-label="Change temperature"
                value={settings.temperature}
                onChange={(value) =>
                  typeof value == 'number' &&
                  onSettingsChange({ ...settings, temperature: value })
                }
                minValue={0}
                maxValue={1}
                step={0.05}
                classNames={{
                  thumb: 'dark:after:bg-white',
                }}
              />
            </InputWrapper>

            <InputWrapper
              label={t('modelSettings.frequencyPenalty.label') ?? ''}
              value={settings.frequencyPenalty}
              description={
                t('modelSettings.frequencyPenalty.description') ?? ''
              }
              tooltip={t('modelSettings.frequencyPenalty.tooltip') ?? ''}
            >
              <Slider
                aria-label="Change frequency penalty"
                value={settings.frequencyPenalty}
                onChange={(value) =>
                  typeof value == 'number' &&
                  onSettingsChange({ ...settings, frequencyPenalty: value })
                }
                minValue={-2}
                maxValue={2}
                step={0.05}
                classNames={{
                  thumb: 'dark:after:bg-white',
                }}
              />
            </InputWrapper>

            <InputWrapper
              label={t('modelSettings.presencePenalty.label') ?? ''}
              description={t('modelSettings.presencePenalty.description') ?? ''}
              value={settings.presencePenalty}
              tooltip={t('modelSettings.presencePenalty.tooltip') ?? ''}
            >
              <Slider
                aria-label="Change presence penalty"
                value={settings.presencePenalty}
                onChange={(value) =>
                  typeof value == 'number' &&
                  onSettingsChange({ ...settings, presencePenalty: value })
                }
                minValue={-2}
                maxValue={2}
                step={0.05}
                classNames={{
                  thumb: 'dark:after:bg-white',
                }}
              />
            </InputWrapper>

            <TextAreaWrapper
              label={t('modelSettings.systemPrompt.label') ?? ''}
              ariaLabel={t('modelSettings.systemPrompt.label') ?? ''}
              placeholder={t('modelSettings.systemPrompt.placeholder') ?? ''}
              value={settings.systemPrompt}
              onChange={(value) =>
                onSettingsChange({ ...settings, systemPrompt: value })
              }
              description={t('modelSettings.systemPrompt.description') ?? ''}
              tooltip={t('modelSettings.systemPrompt.tooltip') ?? ''}
              rows={6}
            />
          </div>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
};

export default SettingsDrawer;
