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
    if (error && error instanceof APIRequestError) {
      toast.error(error.message, {
        icon: errorIcon,
        style: errorStyle,
      });
    } else {
      toast.error(toastContent as ReactNode | string, {
        icon: errorIcon,
        style: errorStyle,
      });
    }
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
