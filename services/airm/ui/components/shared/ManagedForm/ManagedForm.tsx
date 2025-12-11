// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useState } from 'react';
import {
  DefaultValues,
  FieldErrors,
  FieldValues,
  Resolver,
  UseFormReturn,
  useForm,
} from 'react-hook-form';
import { ActionButton } from '@/components/shared/Buttons';
import { zodResolver } from '@hookform/resolvers/zod';
import { v4 as uuidv4 } from 'uuid';
import { ZodType } from 'zod';

interface Props<T extends FieldValues> {
  className?: string;
  defaultValues?: DefaultValues<T>;
  formRef?: React.RefObject<HTMLFormElement | null> | null;
  onFormFailure?: (errors: FieldErrors<T>, data: T) => void;
  onFormSuccess: (data: T) => void;
  validationSchema: ZodType<T>;
  isActioning?: boolean;
  renderFields: (form: UseFormReturn<T>) => React.ReactNode;
  resolver?: (schema: ZodType<T>) => Resolver<T>;
  showResetButton?: boolean;
  showSubmitButton?: boolean;
  submitButtonText?: string;
  resetButtonText?: string;
}

export const ManagedForm = <T extends Record<string, any>>({
  validationSchema,
  className,
  defaultValues,
  onFormFailure,
  onFormSuccess,
  resolver = zodResolver,
  isActioning,
  renderFields,
  showSubmitButton,
  showResetButton,
  resetButtonText,
  submitButtonText,
  formRef,
}: Props<T>) => {
  const [formKey, setFormKey] = useState<string>(uuidv4());

  const form = useForm<T>({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: resolver(validationSchema),
    defaultValues: defaultValues,
    shouldUnregister: true,
  });

  const onSubmit = (data: Record<string, unknown>) => {
    // call onFormSuccess with the parsed data
    if (!isActioning && onFormSuccess) {
      onFormSuccess(data as T);
      form.reset(undefined, { keepDirtyValues: true });
    }
  };

  const onError = (errors: Record<string, unknown>) => {
    // Handle form errors
    if (!isActioning && onFormFailure) {
      onFormFailure(errors as FieldErrors<T>, form.getValues() as T);
    }
  };

  return (
    <form
      ref={formRef}
      onSubmit={form.handleSubmit(onSubmit, onError)}
      className={className}
      key={formKey}
    >
      {renderFields(form)}
      {showResetButton || showSubmitButton ? (
        <div className="flex items-center gap-3 py-4">
          {showResetButton ? (
            <ActionButton
              secondary
              aria-label={resetButtonText}
              isDisabled={isActioning}
              type="button"
              onPress={() => {
                setFormKey(uuidv4());
                form.reset(defaultValues);
              }}
            >
              {resetButtonText}
            </ActionButton>
          ) : null}
          {showSubmitButton ? (
            <ActionButton
              primary
              aria-label={submitButtonText}
              isLoading={isActioning}
              type="submit"
            >
              {submitButtonText}
            </ActionButton>
          ) : null}
        </div>
      ) : null}
    </form>
  );
};

export default ManagedForm;
