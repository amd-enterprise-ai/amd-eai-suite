// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SelectItem, Tab, Tabs } from '@heroui/react';
import { useCallback, useMemo, useState } from 'react';
import { UseFormReturn } from 'react-hook-form';
import { useTranslation } from 'next-i18next';

import FormInput from '@/components/shared/ManagedForm/FormInput';
import FormSelect from '@/components/shared/ManagedForm/FormSelect';

enum TokenSelectorMode {
  EXISTING = 'existing',
  NEW = 'new',
}

interface HuggingFaceTokenSelectorProps {
  form: UseFormReturn<any>;
  existingTokens: { id: string; name: string }[];
  fieldNames?: {
    selectedToken?: string;
    name?: string;
    token?: string;
  };
}

export const HuggingFaceTokenSelector = ({
  form,
  existingTokens,
  fieldNames = {
    selectedToken: 'selectedToken',
    name: 'name',
    token: 'token',
  },
}: HuggingFaceTokenSelectorProps) => {
  const { t } = useTranslation('models');

  const selectedTokenField = fieldNames.selectedToken || 'selectedToken';
  const nameField = fieldNames.name || 'name';
  const tokenField = fieldNames.token || 'token';

  const watchSelectedToken = form.watch(selectedTokenField);
  const watchName = form.watch(nameField);
  const watchToken = form.watch(tokenField);

  // Track user's explicit tab selection when fields are empty
  const [manualModeSelection, setManualModeSelection] =
    useState<TokenSelectorMode | null>(null);

  const currentMode = useMemo(() => {
    const hasSelectedToken = Boolean(watchSelectedToken?.trim());
    const hasManualInput = Boolean(watchName?.trim() || watchToken?.trim());

    // When user has data, mode is derived from the data
    if (hasSelectedToken) return TokenSelectorMode.EXISTING;
    if (hasManualInput) return TokenSelectorMode.NEW;

    // When fields are empty, use manual selection if available
    if (manualModeSelection) return manualModeSelection;

    // Default behavior when no data and no manual selection
    return existingTokens.length > 0
      ? TokenSelectorMode.EXISTING
      : TokenSelectorMode.NEW;
  }, [
    watchSelectedToken,
    watchName,
    watchToken,
    manualModeSelection,
    existingTokens.length,
  ]);

  const handleModeChange = useCallback(
    (mode: string) => {
      const selectedMode = mode as TokenSelectorMode;
      setManualModeSelection(selectedMode);
      if (selectedMode === TokenSelectorMode.EXISTING) {
        form.setValue(nameField, '');
        form.setValue(tokenField, '');
        form.clearErrors([nameField, tokenField]);
      } else {
        form.setValue(selectedTokenField, '');
        form.setValue(nameField, '');
        form.setValue(tokenField, '');
        form.clearErrors([selectedTokenField, nameField, tokenField]);
      }
    },
    [form, selectedTokenField, nameField, tokenField],
  );

  const isNameRequired = currentMode === TokenSelectorMode.NEW;
  const isTokenRequired = currentMode === TokenSelectorMode.NEW;

  return (
    <div className="flex flex-col gap-4">
      <Tabs
        selectedKey={currentMode}
        onSelectionChange={(key) => handleModeChange(key as string)}
        aria-label={t('huggingFaceTokenDrawer.fields.selectMode')}
        classNames={{
          tabList: 'w-full',
          tab: 'flex-1',
        }}
      >
        <Tab
          key={TokenSelectorMode.EXISTING}
          title={t('huggingFaceTokenDrawer.fields.selectExisting')}
          isDisabled={existingTokens.length === 0}
        />
        <Tab
          key={TokenSelectorMode.NEW}
          title={t('huggingFaceTokenDrawer.fields.addNew')}
        />
      </Tabs>

      {currentMode === TokenSelectorMode.EXISTING && (
        <FormSelect
          form={form}
          name={selectedTokenField}
          label={t('huggingFaceTokenDrawer.fields.selectToken.label')}
          placeholder={t(
            'huggingFaceTokenDrawer.fields.selectToken.placeholder',
          )}
          selectedKeys={watchSelectedToken ? [watchSelectedToken] : []}
          onSelectionChange={(keys) => {
            const selectedKey = Array.from(keys)[0] as string;
            form.setValue(selectedTokenField, selectedKey);
            form.clearErrors([selectedTokenField]);
          }}
        >
          {existingTokens.map((token) => (
            <SelectItem key={token.id}>{token.name}</SelectItem>
          ))}
        </FormSelect>
      )}

      {currentMode === TokenSelectorMode.NEW && (
        <>
          <FormInput
            form={form}
            name={nameField}
            label={t('huggingFaceTokenDrawer.fields.name.label')}
            placeholder={t('huggingFaceTokenDrawer.fields.name.placeholder')}
            isRequired={isNameRequired}
            autoComplete="off"
            data-form-type="other"
          />

          <FormInput
            form={form}
            name={tokenField}
            label={t('huggingFaceTokenDrawer.fields.token.label')}
            type="password"
            placeholder={t('huggingFaceTokenDrawer.fields.token.placeholder')}
            isRequired={isTokenRequired}
            autoComplete="new-password"
            data-form-type="other"
          />
        </>
      )}
    </div>
  );
};

export default HuggingFaceTokenSelector;
