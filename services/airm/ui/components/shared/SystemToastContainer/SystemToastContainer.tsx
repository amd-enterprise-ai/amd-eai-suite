// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconX } from '@tabler/icons-react';
import { Bounce, ToastContainer } from 'react-toastify';

import { useTheme } from 'next-themes';

export const SystemToastContainer = () => {
  const { theme } = useTheme();
  return (
    <ToastContainer
      position="top-right"
      autoClose={5000}
      pauseOnFocusLoss
      draggable
      pauseOnHover
      transition={Bounce}
      closeButton={<IconX size={16} className="ml-auto" />}
      theme={theme}
      closeOnClick
      hideProgressBar
    />
  );
};

export default SystemToastContainer;
