// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button } from '@heroui/react';
import {
  IconChevronDown,
  IconExclamationCircleFilled,
  IconRefresh,
} from '@tabler/icons-react';
import { useState } from 'react';

import { useTranslation } from 'next-i18next';
import { useRouter } from 'next/router';
import { ActionButton } from '@/components/shared/Buttons';
import { ErrorCodes, ErrorMessageProps } from '@/types/errors';

function ErrorMessage({ message = '', code, onRefresh }: ErrorMessageProps) {
  const { t } = useTranslation();
  const [isErrorExpanded, setIsErrorExpanded] = useState(false);
  const router = useRouter();

  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh();
    } else {
      router.replace(router.asPath);
    }
  };

  const toggleErrorDetails = () => {
    setIsErrorExpanded(!isErrorExpanded);
  };

  const isKnownError = Object.values(ErrorCodes).includes(code as ErrorCodes);

  return (
    <div className="w-full h-full flex justify-center items-center">
      <div className="dark:bg-default-50 max-w-[400px] flex flex-col items-start border dark:border-default-100 border-default-200 p-12 rounded-md text-default">
        <IconExclamationCircleFilled className="text-danger" size="48" />
        <div className="flex flex-col gap-4 my-8">
          <h1>
            {isKnownError ? t(`error.${code}.title`) : t(`error.unknown.title`)}
          </h1>
          <p>
            {isKnownError
              ? t(`error.${code}.description`)
              : t(`error.unknown.description`)}
          </p>
          {message && (
            <div className="w-full mt-2">
              <Button
                size="sm"
                variant="ghost"
                onPress={toggleErrorDetails}
                endContent={
                  <IconChevronDown
                    size={16}
                    className={`transition-transform ${
                      isErrorExpanded ? 'rotate-180' : ''
                    }`}
                  />
                }
              >
                {t('actions.showDetails.title')}
              </Button>
              <div
                className={`overflow-hidden transition-all duration-300 ${
                  isErrorExpanded ? 'max-h-24 opacity-100' : 'max-h-0 opacity-0'
                }`}
              >
                <div className="text-default-700 text-sm mt-3 rounded-md break-all">
                  {t('error.label')}: {message}
                </div>
              </div>
            </div>
          )}
        </div>
        <ActionButton
          className="mt-4"
          onPress={handleRefresh}
          icon={<IconRefresh size={18} />}
        >
          {t(`error.refreshActionLabel`)}
        </ActionButton>
      </div>
    </div>
  );
}

export default ErrorMessage;
