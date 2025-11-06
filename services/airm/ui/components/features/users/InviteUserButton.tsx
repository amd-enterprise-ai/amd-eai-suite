// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useAccessControl } from '@/hooks/useAccessControl';
import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  onClick: () => void;
  label: string;
}

export const InviteUserButton = ({ onClick, label }: Props) => {
  const { isInviteEnabled } = useAccessControl();

  return (
    <>
      {isInviteEnabled && (
        <ActionButton primary aria-label={label} onPress={onClick}>
          {label}
        </ActionButton>
      )}
    </>
  );
};
