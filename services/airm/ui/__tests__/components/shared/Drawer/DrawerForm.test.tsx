// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import { DrawerForm } from '@/components/shared/Drawer';
import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';

import '@testing-library/jest-dom';
import { ZodType, z } from 'zod';

type SampleFormData = {
  username: string;
};

const sampleFormSchema: ZodType<SampleFormData> = z.object({
  username: z.string().trim().nonempty('Username is required'),
});

describe('DrawerForm', () => {
  it('renders the drawer with form elements', () => {
    act(() => {
      render(
        <DrawerForm<SampleFormData>
          isOpen={true}
          isActioning={false}
          validationSchema={sampleFormSchema}
          title="Add User"
          cancelText={'cancel'}
          confirmText={'confirm'}
          renderFields={(form) => (
            <>
              <FormFieldComponent<SampleFormData>
                formField={{
                  name: 'username',
                  label: 'Username',
                  placeholder: 'Enter username',
                  isRequired: true,
                }}
                errorMessage={form.formState.errors.username?.message}
                register={form.register}
                defaultValue={form.getValues('username')}
              />
              <span>Extra Content</span>
            </>
          )}
        />,
      );
    });

    expect(screen.getByText('Add User')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter username')).toBeInTheDocument();
    expect(screen.getByText('Extra Content')).toBeInTheDocument();
  });

  it('validates form fields and shows error messages', () => {
    act(() => {
      render(
        <DrawerForm<SampleFormData>
          isOpen={true}
          isActioning={false}
          validationSchema={sampleFormSchema}
          title="Add User"
          cancelText={'cancel'}
          confirmText={'modal.addUser.actions.confirm'}
          renderFields={(form) => (
            <>
              <FormFieldComponent<SampleFormData>
                formField={{
                  name: 'username',
                  label: 'Username',
                  placeholder: 'Enter username',
                  isRequired: true,
                }}
                errorMessage={form.formState.errors.username?.message}
                register={form.register}
                defaultValue={form.getValues('username')}
              />
              <span>Extra Content</span>
            </>
          )}
        />,
      );
    });

    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    act(() => {
      fireEvent.click(actionButton);
    });
    expect(screen.getByPlaceholderText('Enter username')).toHaveFocus();
  });

  it('calls onFormSuccess with form data when form is valid', async () => {
    const onFormSuccess = vi.fn();
    await act(() => {
      render(
        <DrawerForm<SampleFormData>
          isOpen={true}
          isActioning={false}
          validationSchema={sampleFormSchema}
          title="Add User"
          cancelText={'cancel'}
          confirmText={'modal.addUser.actions.confirm'}
          onFormSuccess={onFormSuccess}
          renderFields={(form) => (
            <>
              <FormFieldComponent<SampleFormData>
                formField={{
                  name: 'username',
                  label: 'Username',
                  placeholder: 'Enter username',
                  isRequired: true,
                }}
                errorMessage={form.formState.errors.username?.message}
                register={form.register}
                defaultValue={form.getValues('username')}
              />
              <span>Extra Content</span>
            </>
          )}
        />,
      );
    });

    await act(() => {
      fireEvent.change(screen.getByPlaceholderText('Enter username'), {
        target: { value: 'testuser' },
      });

      fireEvent.click(
        screen.getByRole('button', { name: 'modal.addUser.actions.confirm' }),
      );
    });

    expect(onFormSuccess).toHaveBeenCalledWith({ username: 'testuser' });
  });
});
