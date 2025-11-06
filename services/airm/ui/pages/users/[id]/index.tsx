// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useRouter } from 'next/router';

import useSystemToast from '@/hooks/useSystemToast';

import { fetchUser, updateUser } from '@/services/app/users';
import { getProjects } from '@/services/server/projects';
import { getUser } from '@/services/server/users';

import { APIRequestError } from '@/utils/app/errors';
import { authOptions } from '@/utils/server/auth';

import { ProjectWithResourceAllocation } from '@/types/projects';
import { UserFormData, UserWithProjects } from '@/types/users';

import { DeleteUser, Projects, UserRoles } from '@/components/features/user';
import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';
import ManagedForm from '@/components/shared/ManagedForm/ManagedForm';

import { ZodType, z } from 'zod';

const translationKeySet = 'users';

interface Props {
  user: UserWithProjects;
  projects: ProjectWithResourceAllocation[];
}

const UserPage: React.FC<Props> = ({ user, projects }) => {
  const router = useRouter();
  const { id } = router.query;
  const { t } = useTranslation(translationKeySet);
  const { toast } = useSystemToast();

  const { data: userData } = useQuery<UserWithProjects>({
    queryKey: ['user'],
    queryFn: () => fetchUser(id as string),
    initialData: user,
  });

  const queryClient = useQueryClient();

  const { mutate: updateUserMutation, isPending } = useMutation({
    mutationFn: updateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
      toast.success(t('detail.edit.notification.success'));
    },
    onError: (error) => {
      toast.error(
        t('detail.edit.notification.error'),
        error as APIRequestError,
      );
      console.error('Error saving user', error);
    },
  });

  const userFormSchema: ZodType<UserFormData> = useMemo(
    () =>
      z.object({
        firstName: z
          .string()
          .trim()
          .min(2, t('detail.form.firstName.validation.length') || '')
          .max(64, t('detail.form.firstName.validation.length') || '')
          .nonempty(t('detail.form.firstName.validation.required') || ''),
        lastName: z
          .string()
          .trim()
          .min(2, t('detail.form.lastName.validation.length') || '')
          .max(64, t('detail.form.lastName.validation.length') || '')
          .nonempty(t('detail.form.lastName.validation.required') || ''),
        email: z.string().email(t('detail.form.email.validation.format') || ''),
      }),
    [t],
  );

  const defaultValues = {
    firstName: userData.firstName,
    lastName: userData.lastName,
    email: userData.email,
  };

  return (
    <div className="flex flex-col">
      <div className="flex gap-4">
        <section className="p-8 w-3/4 min-h-full px-8 font-bold">
          <div className="border-1 rounded-sm p-4 bg-white dark:bg-black">
            <h2 className="p-1">{t('detail.title')}</h2>
            <ManagedForm<UserFormData>
              className="flex gap-4 my-4 flex-col w-3/4"
              defaultValues={defaultValues}
              validationSchema={userFormSchema}
              showResetButton
              showSubmitButton
              isActioning={isPending}
              onFormSuccess={(data) =>
                updateUserMutation({
                  id: userData.id,
                  firstName: (data['firstName'] as string).trim(),
                  lastName: (data['lastName'] as string).trim(),
                })
              }
              submitButtonText={t('detail.form.actions.submit') || ''}
              resetButtonText={t('detail.form.actions.reset') || ''}
              renderFields={(form) => (
                <div className="flex flex-col gap-4">
                  <div className="flex gap-4 w-full">
                    <FormFieldComponent<UserFormData>
                      formField={{
                        name: 'firstName',
                        label: t('detail.form.firstName.label'),
                        placeholder: t('detail.form.firstName.placeholder'),
                        props: {
                          maxLength: 64,
                        },
                      }}
                      defaultValue={form.formState.defaultValues?.firstName}
                      errorMessage={form.formState.errors.firstName?.message}
                      register={form.register}
                    />
                    <FormFieldComponent<UserFormData>
                      formField={{
                        name: 'lastName',
                        label: t('detail.form.lastName.label'),
                        placeholder: t('detail.form.lastName.placeholder'),
                        props: {
                          maxLength: 64,
                        },
                      }}
                      defaultValue={form.formState.defaultValues?.lastName}
                      errorMessage={form.formState.errors.lastName?.message}
                      register={form.register}
                    />
                  </div>
                  <FormFieldComponent<UserFormData>
                    formField={{
                      name: 'email',
                      label: t('detail.form.email.label'),
                      placeholder: t('detail.form.email.placeholder'),
                      isReadOnly: true,
                    }}
                    defaultValue={form.formState.defaultValues?.email}
                    errorMessage={form.formState.errors.email?.message}
                    register={form.register}
                  />
                </div>
              )}
            />
          </div>
          <DeleteUser id={userData.id} email={userData.email} />
        </section>
        <section className="border-l-1 p-8 dark:border-gray-800 w-1/4 min-h-full min-w-96">
          <h2>{t('detail.projectsAndRoles.title')}</h2>
          <Projects user={userData} projects={projects} />
          <UserRoles user={userData} />
        </section>
      </div>
    </div>
  );
};

export default UserPage;

export const getServerSideProps = async (context: any) => {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  try {
    const userResponse = await getUser(
      context.params.id,
      session?.accessToken as string,
    );

    const projectsResponse = await getProjects(session?.accessToken as string);

    const translations = await serverSideTranslations(locale, [
      'common',
      'users',
    ]);

    const breadcrumb = [
      {
        title:
          translations._nextI18Next?.initialI18nStore[locale]?.users?.title,
        href: '/users',
      },
      {
        title: `${userResponse?.firstName} ${userResponse?.lastName}` || '',
      },
    ];

    return {
      props: {
        ...translations,
        user: userResponse,
        projects: projectsResponse.projects,
        pageBreadcrumb: breadcrumb,
      },
    };
  } catch (error) {
    console.error('User not found: ' + error);
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }
};
