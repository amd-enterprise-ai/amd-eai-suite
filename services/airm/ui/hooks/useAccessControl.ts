// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useQuery } from '@tanstack/react-query';
import { useSession } from 'next-auth/react';
import { fetchOrganization } from '@/services/app/organizations';
import { Organization } from '@/types/organization';
import { UserRole } from '@/types/enums/user-roles';

/**
 * Custom hook to determine access control capabilities
 *
 * Access Control Rules:
 * 1. If SSO is configured (idpLinked=true):
 *    - User invitation is disabled (isInviteEnabled=false)
 *    - User role management is read-only (isRoleManagementEnabled=false)
 *
 * 2. If no SSO (idpLinked=false) and no SMTP (smtpEnabled=false):
 *    - User invitation is disabled (isInviteEnabled=false)
 *    - User role management is enabled (isRoleManagementEnabled=true)
 *
 * 3. If no SSO (idpLinked=false) and SMTP enabled (smtpEnabled=true):
 *    - User invitation is enabled (isInviteEnabled=true)
 *    - User role management is enabled (isRoleManagementEnabled=true)
 */
export const useAccessControl = () => {
  const { data: session } = useSession();
  const { data: organization } = useQuery<Organization>({
    queryKey: ['organization', session?.accessToken],
    queryFn: fetchOrganization,
    staleTime: Infinity,
    gcTime: Infinity,
    enabled: !!session?.accessToken,
    retry: 1,
  });

  const isRoleManagementEnabled = organization
    ? !organization.idpLinked
    : false;

  const isInviteEnabled = organization
    ? organization.smtpEnabled && !organization.idpLinked
    : false;

  const isAdministrator =
    (session?.user?.roles &&
      session.user.roles.includes(UserRole.PLATFORM_ADMIN)) ||
    false;

  return {
    isRoleManagementEnabled,
    isInviteEnabled,
    isAdministrator,
  };
};
