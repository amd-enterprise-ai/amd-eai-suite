// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ListboxItem, ListboxSection } from '../Listbox/Listbox';
import { Select, SelectItem, type Selection } from '../Select/Select';
import { Input } from '../Input/InputPrimitive';
import { IconPlus } from '@tabler/icons-react';
import { useCallback, useMemo, useState } from 'react';

import { ActionButton } from '../Buttons';
import { CloseButton } from '../Buttons/CloseButton';
import {
  ModalPrimitive,
  ModalPrimitiveBody,
  ModalPrimitiveContent,
  ModalPrimitiveFooter,
  ModalPrimitiveHeader,
} from '../Modal/ModalPrimitive';

export interface HuggingFaceTokenOption {
  /** Kubernetes secret name sent to the API as `hfTokenSecretName`. */
  name: string;
  /** Human-friendly label shown in the dropdown. */
  displayName: string;
}

export interface HuggingFaceTokenSelectorLabels {
  selectLabel: string;
  selectPlaceholder: string;
  addNewItemLabel: string;

  dialogTitle: string;
  dialogNameLabel: string;
  dialogNamePlaceholder: string;
  dialogTokenLabel: string;
  dialogTokenPlaceholder: string;
  dialogCancelLabel: string;
  dialogSubmitLabel: string;
}

export interface HuggingFaceTokenSelectorProps {
  /** Currently selected token name (controlled). */
  value: string | null | undefined;
  /** Emits the name of the newly selected token. */
  onChange: (name: string) => void;
  /** Existing tokens available to the project/namespace. */
  existingTokens: HuggingFaceTokenOption[];
  /**
   * Creates a new HF token on the backend. Implementations should
   * persist the token secret and return its server-assigned `name`;
   * the selector will auto-select that token after creation.
   */
  onCreateToken: (input: {
    name: string;
    token: string;
  }) => Promise<{ name: string }>;
  /** Display label and placeholders. Required so consumers own their i18n. */
  labels: HuggingFaceTokenSelectorLabels;

  isRequired?: boolean;
  isDisabled?: boolean;
  isInvalid?: boolean;
  errorMessage?: string;
  className?: string;
  /** Test handle for the root select control. */
  'data-testid'?: string;
}

// Sentinel key used by the dropdown to recognise the "+ Add new token" row.
// Must be a value that cannot collide with a real Kubernetes secret name
// (which is restricted to lowercase alphanumerics, '-' and '.').
const ADD_NEW_KEY = '__add_new_hf_token__';

/**
 * Dropdown selector for an existing Hugging Face access token,
 * with an inline "+ Add new" affordance that opens a create-token dialog.
 *
 * Presentational: data loading and persistence are owned by the consumer
 * via `existingTokens` / `onCreateToken`. The selector keeps no internal
 * state about the selected token — pass `value`/`onChange` to control it.
 */
export const HuggingFaceTokenSelector = ({
  value,
  onChange,
  existingTokens,
  onCreateToken,
  labels,
  isRequired,
  isDisabled,
  isInvalid,
  errorMessage,
  className,
  'data-testid': dataTestId,
}: HuggingFaceTokenSelectorProps) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [dialogName, setDialogName] = useState('');
  const [dialogToken, setDialogToken] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const selectedKeys = useMemo<Set<string>>(
    () => (value ? new Set([value]) : new Set()),
    [value],
  );

  const handleSelectionChange = useCallback(
    (keys: Selection) => {
      // HeroUI's Selection is `'all' | Set<Key>`. This selector is single-
      // select, so `'all'` is not meaningful here. Guard it explicitly so
      // we don't fall into the `Array.from(keys)` branch and treat the
      // sentinel string as an iterable of characters (which would select
      // 'a' instead of any real key).
      if (keys === 'all') return;
      const next = Array.from(keys)[0];
      if (next === ADD_NEW_KEY) {
        setIsDialogOpen(true);
        return;
      }
      if (typeof next === 'string') {
        onChange(next);
      }
    },
    [onChange],
  );

  const resetDialog = useCallback(() => {
    setDialogName('');
    setDialogToken('');
    setSubmitError(null);
    setIsSubmitting(false);
  }, []);

  const handleDialogClose = useCallback(() => {
    if (isSubmitting) return;
    setIsDialogOpen(false);
    resetDialog();
  }, [isSubmitting, resetDialog]);

  const handleDialogSubmit = useCallback(async () => {
    const trimmedName = dialogName.trim();
    const trimmedToken = dialogToken.trim();
    if (!trimmedName || !trimmedToken) return;

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const created = await onCreateToken({
        name: trimmedName,
        token: trimmedToken,
      });
      onChange(created.name);
      setIsDialogOpen(false);
      resetDialog();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err));
      setIsSubmitting(false);
    }
  }, [dialogName, dialogToken, onChange, onCreateToken, resetDialog]);

  const submitDisabled =
    !dialogName.trim() || !dialogToken.trim() || isSubmitting;

  return (
    <div className={className}>
      <Select
        label={labels.selectLabel}
        labelPlacement="outside"
        placeholder={labels.selectPlaceholder}
        variant="bordered"
        selectedKeys={selectedKeys}
        onSelectionChange={handleSelectionChange}
        isRequired={isRequired}
        isDisabled={isDisabled}
        isInvalid={isInvalid}
        errorMessage={errorMessage}
        data-testid={dataTestId}
        listboxProps={{
          'aria-label': labels.selectLabel,
        }}
      >
        <ListboxSection showDivider>
          {existingTokens.map((token) => (
            <SelectItem key={token.name} textValue={token.displayName}>
              {token.displayName}
            </SelectItem>
          ))}
        </ListboxSection>
        <ListboxItem
          key={ADD_NEW_KEY}
          startContent={<IconPlus size={16} aria-hidden />}
          className="text-primary"
          textValue={labels.addNewItemLabel}
          data-testid="hf-token-selector-add-new"
        >
          {labels.addNewItemLabel}
        </ListboxItem>
      </Select>

      <ModalPrimitive
        isOpen={isDialogOpen}
        onOpenChange={handleDialogClose}
        isDismissable={!isSubmitting}
        hideCloseButton={isSubmitting}
        closeButton={<CloseButton />}
        classNames={{
          base: 'overflow-y-auto overflow-x-hidden',
          header: 'border-b-1 border-default-200 w-full pr-[64px]',
          body: 'py-6',
          footer: 'justify-end w-full',
        }}
      >
        <ModalPrimitiveContent>
          <ModalPrimitiveHeader>{labels.dialogTitle}</ModalPrimitiveHeader>
          <ModalPrimitiveBody>
            <div className="flex flex-col gap-4">
              <Input
                label={labels.dialogNameLabel}
                labelPlacement="outside"
                placeholder={labels.dialogNamePlaceholder}
                value={dialogName}
                onValueChange={setDialogName}
                isDisabled={isSubmitting}
                isRequired
                data-testid="hf-token-selector-dialog-name"
              />
              <Input
                label={labels.dialogTokenLabel}
                labelPlacement="outside"
                placeholder={labels.dialogTokenPlaceholder}
                type="password"
                value={dialogToken}
                onValueChange={setDialogToken}
                isDisabled={isSubmitting}
                isRequired
                autoComplete="new-password"
                data-testid="hf-token-selector-dialog-token"
              />
              {submitError ? (
                <p className="text-danger text-sm" role="alert">
                  {submitError}
                </p>
              ) : null}
            </div>
          </ModalPrimitiveBody>
          <ModalPrimitiveFooter>
            <ActionButton
              secondary
              aria-label={labels.dialogCancelLabel}
              onPress={handleDialogClose}
              isDisabled={isSubmitting}
            >
              {labels.dialogCancelLabel}
            </ActionButton>
            <ActionButton
              primary
              aria-label={labels.dialogSubmitLabel}
              onPress={handleDialogSubmit}
              isLoading={isSubmitting}
              isDisabled={submitDisabled}
              data-testid="hf-token-selector-dialog-submit"
            >
              {labels.dialogSubmitLabel}
            </ActionButton>
          </ModalPrimitiveFooter>
        </ModalPrimitiveContent>
      </ModalPrimitive>
    </div>
  );
};

export default HuggingFaceTokenSelector;
