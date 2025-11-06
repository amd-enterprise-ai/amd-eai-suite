// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SelectItem } from '@heroui/react';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { z, ZodType } from 'zod';
import { vi } from 'vitest';

import { HuggingFaceTokenSelector } from '@/components/shared/HuggingFaceTokenSelector';
import ManagedForm from '@/components/shared/ManagedForm/ManagedForm';
import { HuggingFaceTokenData } from '@/types/secrets';

// Mock useTranslation
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const formSchema: ZodType<HuggingFaceTokenData> = z.object({
  selectedToken: z.string().optional(),
  name: z.string().optional(),
  token: z.string().optional(),
});

const mockExistingTokens = [
  { id: 'token-1', name: 'Production Token' },
  { id: 'token-2', name: 'Development Token' },
];

const renderHuggingFaceTokenSelector = (
  existingTokens: { id: string; name: string }[] = mockExistingTokens,
  formProps: Partial<
    React.ComponentProps<typeof ManagedForm<HuggingFaceTokenData>>
  > = {},
) => {
  const defaultFormProps = {
    onFormSuccess: vi.fn(),
    validationSchema: formSchema,
    defaultValues: { selectedToken: '', name: '', token: '' },
  };

  return render(
    <ManagedForm<HuggingFaceTokenData>
      {...defaultFormProps}
      {...formProps}
      renderFields={(form) => (
        <HuggingFaceTokenSelector form={form} existingTokens={existingTokens} />
      )}
    />,
  );
};

describe('HuggingFaceTokenSelector', () => {
  describe('Rendering', () => {
    it('renders both tabs when existing tokens are available', () => {
      renderHuggingFaceTokenSelector();

      expect(
        screen.getByText('huggingFaceTokenDrawer.fields.selectExisting'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('huggingFaceTokenDrawer.fields.addNew'),
      ).toBeInTheDocument();
    });

    it('renders with "Select existing" tab active by default when tokens exist', () => {
      renderHuggingFaceTokenSelector();

      const selectTokenTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.selectExisting/i,
      });
      expect(selectTokenTab).toHaveAttribute('aria-selected', 'true');
    });

    it('renders with "Add new" tab active by default when no tokens exist', () => {
      renderHuggingFaceTokenSelector([]);

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      expect(addNewTab).toHaveAttribute('aria-selected', 'true');
    });

    it('disables "Select existing" tab when no tokens exist', () => {
      renderHuggingFaceTokenSelector([]);

      const selectTokenTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.selectExisting/i,
      });
      expect(selectTokenTab).toHaveAttribute('aria-disabled', 'true');
    });

    it('renders dropdown when "Select existing" tab is active', () => {
      renderHuggingFaceTokenSelector();

      expect(
        screen.getByRole('button', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        }),
      ).toBeInTheDocument();
    });

    it('renders input fields when "Add new" tab is active', () => {
      renderHuggingFaceTokenSelector();

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      expect(
        screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
      ).toBeInTheDocument();
    });
  });

  describe('Tab Switching', () => {
    it('switches from "Select existing" to "Add new" when clicking Add new tab', async () => {
      renderHuggingFaceTokenSelector();

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
        ).toBeInTheDocument();
        expect(
          screen.getByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
        ).toBeInTheDocument();
      });

      expect(
        screen.queryByRole('button', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        }),
      ).not.toBeInTheDocument();
    });

    it('switches from "Add new" to "Select existing" when clicking Select existing tab', async () => {
      renderHuggingFaceTokenSelector();

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
        ).toBeInTheDocument();
      });

      const selectExistingTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.selectExisting/i,
      });
      fireEvent.click(selectExistingTab);

      await waitFor(() => {
        expect(
          screen.getByRole('button', {
            name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
          }),
        ).toBeInTheDocument();
      });

      expect(
        screen.queryByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
      ).not.toBeInTheDocument();
    });

    it('clears manual input fields when switching to "Select existing" tab', async () => {
      const onFormSuccess = vi.fn();
      renderHuggingFaceTokenSelector(mockExistingTokens, {
        onFormSuccess,
        showSubmitButton: true,
        submitButtonText: 'Submit',
      });

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
        ).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText(
        /huggingFaceTokenDrawer.fields.name.label/i,
      );
      const tokenInput = screen.getByLabelText(
        /huggingFaceTokenDrawer.fields.token.label/i,
      );

      fireEvent.change(nameInput, { target: { value: 'Test Token' } });
      fireEvent.change(tokenInput, { target: { value: 'hf_testtoken123' } });

      const selectExistingTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.selectExisting/i,
      });
      fireEvent.click(selectExistingTab);

      await waitFor(() => {
        const addNewTabAgain = screen.getByRole('tab', {
          name: /huggingFaceTokenDrawer.fields.addNew/i,
        });
        fireEvent.click(addNewTabAgain);
      });

      await waitFor(() => {
        const clearedNameInput = screen.getByLabelText(
          /huggingFaceTokenDrawer.fields.name.label/i,
        );
        const clearedTokenInput = screen.getByLabelText(
          /huggingFaceTokenDrawer.fields.token.label/i,
        );
        expect(clearedNameInput).toHaveValue('');
        expect(clearedTokenInput).toHaveValue('');
      });
    });

    it('clears selected token when switching to "Add new" tab', async () => {
      renderHuggingFaceTokenSelector();

      const selectButton = screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      });
      fireEvent.click(selectButton);

      await waitFor(() => {
        expect(
          screen.getByRole('option', { name: 'Production Token' }),
        ).toBeInTheDocument();
      });

      const productionTokenOption = screen.getByRole('option', {
        name: 'Production Token',
      });
      fireEvent.click(productionTokenOption);

      // Wait for dropdown to close
      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
      });

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      const selectExistingTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.selectExisting/i,
      });
      fireEvent.click(selectExistingTab);

      await waitFor(() => {
        const selectButtonAgain = screen.getByRole('button', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        });
        expect(selectButtonAgain).toBeInTheDocument();
      });
    });
  });

  describe('Form Interactions', () => {
    it('allows typing in Name field when in "Add new" mode', async () => {
      renderHuggingFaceTokenSelector();

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
        ).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText(
        /huggingFaceTokenDrawer.fields.name.label/i,
      );
      fireEvent.change(nameInput, { target: { value: 'My New Token' } });

      expect(nameInput).toHaveValue('My New Token');
    });

    it('allows typing in Token field when in "Add new" mode', async () => {
      renderHuggingFaceTokenSelector();

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
        ).toBeInTheDocument();
      });

      const tokenInput = screen.getByLabelText(
        /huggingFaceTokenDrawer.fields.token.label/i,
      );
      fireEvent.change(tokenInput, { target: { value: 'hf_abc123' } });

      expect(tokenInput).toHaveValue('hf_abc123');
    });

    it('allows selecting from dropdown when in "Select existing" mode', async () => {
      renderHuggingFaceTokenSelector();

      const selectButton = screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      });
      fireEvent.click(selectButton);

      await waitFor(() => {
        expect(
          screen.getByRole('option', { name: 'Production Token' }),
        ).toBeInTheDocument();
      });

      const productionTokenOption = screen.getByRole('option', {
        name: 'Production Token',
      });
      fireEvent.click(productionTokenOption);

      await waitFor(() => {
        const selectButtonAfterSelection = screen.getByRole('button', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        });
        expect(selectButtonAfterSelection.textContent).toContain(
          'Production Token',
        );
      });
    });
  });

  describe('Derived State Behavior', () => {
    it('stays in "Add new" mode when Name field has value', async () => {
      renderHuggingFaceTokenSelector();

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
        ).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText(
        /huggingFaceTokenDrawer.fields.name.label/i,
      );
      fireEvent.change(nameInput, { target: { value: 'Test' } });

      expect(
        screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
      ).toBeInTheDocument();
    });

    it('stays in "Add new" mode when Token field has value', async () => {
      renderHuggingFaceTokenSelector();

      const addNewTab = screen.getByRole('tab', {
        name: /huggingFaceTokenDrawer.fields.addNew/i,
      });
      fireEvent.click(addNewTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
        ).toBeInTheDocument();
      });

      const tokenInput = screen.getByLabelText(
        /huggingFaceTokenDrawer.fields.token.label/i,
      );
      fireEvent.change(tokenInput, { target: { value: 'hf_test' } });

      expect(
        screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
      ).toBeInTheDocument();
    });

    it('stays in "Select existing" mode when a token is selected', async () => {
      renderHuggingFaceTokenSelector();

      const selectButton = screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      });
      fireEvent.click(selectButton);

      await waitFor(() => {
        expect(
          screen.getByRole('option', { name: 'Production Token' }),
        ).toBeInTheDocument();
      });

      const productionTokenOption = screen.getByRole('option', {
        name: 'Production Token',
      });
      fireEvent.click(productionTokenOption);

      await waitFor(() => {
        expect(
          screen.getByRole('button', {
            name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
          }),
        ).toBeInTheDocument();
      });

      expect(
        screen.queryByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
      ).not.toBeInTheDocument();
    });
  });
});
