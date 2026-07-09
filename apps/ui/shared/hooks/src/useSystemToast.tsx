// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
} from '@tabler/icons-react';
import { ReactNode } from 'react';
import { ToastOptions, toast } from 'react-toastify';

import { APIRequestError } from '@amdenterpriseai/utils/app';

import { ErrorToast } from './ErrorToast';

export const useSystemToast = () => {
  const _toast = (
    toastContent: ReactNode | string,
    toastOptions: ToastOptions<unknown> | undefined,
  ) => {
    toast(toastContent, toastOptions);
  };

  /** Error toast **/
  const errorIcon = () => <IconAlertTriangle className="text-danger" />;

  const errorStyle = {
    background: 'var(--toastify-background-error)',
    color: 'var(--toastify-text-error)',
    lineHeight: '1.3',
  };

  _toast.error = (
    toastContent: ReactNode | string,
    error?: APIRequestError | Error,
  ) => {
    const message =
      error instanceof APIRequestError ? error.message : toastContent;

    // Only a plain-text message can be placed on the clipboard; richer content
    // (e.g. a LinkToast) is shown without a copy affordance.
    const copyText = typeof message === 'string' ? message : undefined;

    toast.error(<ErrorToast content={message} copyText={copyText} />, {
      icon: errorIcon,
      style: errorStyle,
    });
  };

  _toast.info = (toastContent: ReactNode | string) => {
    toast.info(toastContent, {
      icon: <IconInfoCircle className="text-primary" />,
      style: {
        lineHeight: '1.3',
      },
    });
  };

  _toast.warning = (toastContent: ReactNode | string) => {
    toast.warning(toastContent, {
      icon: <IconAlertTriangle className="text-warning" />,
      style: {
        background: 'var(--toastify-background-warning)',
        color: 'var(--toastify-text-warning)',
        lineHeight: '1.3',
      },
    });
  };

  _toast.success = (toastContent: ReactNode | string) => {
    toast.success(toastContent, {
      icon: <IconCircleCheck className="text-success" />,
      style: {
        lineHeight: '1.3',
      },
    });
  };

  return {
    toast: _toast,
  };
};

export default useSystemToast;
