// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import FormFileUpload from '@/components/shared/ManagedForm/FormFileUpload/FormFileUpload';
import ManagedForm from '@/components/shared/ManagedForm/ManagedForm';

import userEvent from '@testing-library/user-event';
import { ZodType, z } from 'zod';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { count?: number }) => {
      const translations: Record<string, string> = {
        drop: options?.count === 1 ? 'Drop file here' : 'Drop files here',
        dropFail:
          options?.count === 1 ? 'Invalid file type' : 'Invalid file types',
        add: options?.count === 1 ? 'Add file' : 'Add files',
        footerFiles: `${options?.count || 0} file${options?.count === 1 ? '' : 's'}`,
      };
      return translations[key] || key;
    },
  }),
}));

// Mock HTMLInputElement to allow setting the files property
Object.defineProperty(HTMLInputElement.prototype, 'files', {
  get() {
    return this._files || null;
  },
  set(value) {
    this._files = value;
  },
  configurable: true,
});

// Mock displayBytesInOptimalUnit
vi.mock('@/utils/app/memory', () => ({
  displayBytesInOptimalUnit: (bytes: number) => `${bytes} bytes`,
}));

type SingleFileFormData = {
  singleFile: File | null;
};

type MultipleFileFormData = {
  multipleFiles: FileList | null;
};

const singleFileFormSchema: ZodType<SingleFileFormData> = z.object({
  singleFile: z
    .instanceof(File)
    .nullable()
    .refine((file) => file !== null, 'File is required'),
});

const multipleFileFormSchema: ZodType<MultipleFileFormData> = z.object({
  multipleFiles: z
    .custom<FileList>()
    .nullable()
    .refine(
      (files) => files !== null && files.length > 0,
      'At least one file is required',
    ),
});

// Helper function to create a mock file
const createMockFile = (
  name: string,
  size: number = 1024,
  type: string = 'text/plain',
): File => {
  const file = new File(['content'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

// Helper function to render FormFileUpload with single file support
const renderSingleFileUpload = (
  formProps: Partial<
    React.ComponentProps<typeof ManagedForm<SingleFileFormData>>
  > = {},
  inputProps: Partial<
    React.ComponentProps<typeof FormFileUpload<SingleFileFormData>>
  > = {},
) => {
  const defaultFormProps = {
    onFormSuccess: vi.fn(),
    validationSchema: singleFileFormSchema,
    defaultValues: { singleFile: null },
  };

  return render(
    <ManagedForm<SingleFileFormData>
      {...defaultFormProps}
      {...formProps}
      renderFields={(form) => (
        <FormFileUpload<SingleFileFormData>
          form={form}
          name="singleFile"
          label="Single File"
          placeholder="Upload a single file"
          multiple={false}
          {...inputProps}
        />
      )}
    />,
  );
};

// Helper function to render FormFileUpload with multiple file support
const renderMultipleFileUpload = (
  formProps: Partial<
    React.ComponentProps<typeof ManagedForm<MultipleFileFormData>>
  > = {},
  inputProps: Partial<
    React.ComponentProps<typeof FormFileUpload<MultipleFileFormData>>
  > = {},
) => {
  const defaultFormProps = {
    onFormSuccess: vi.fn(),
    validationSchema: multipleFileFormSchema,
    defaultValues: { multipleFiles: null },
  };

  return render(
    <ManagedForm<MultipleFileFormData>
      {...defaultFormProps}
      {...formProps}
      renderFields={(form) => (
        <FormFileUpload<MultipleFileFormData>
          form={form}
          name="multipleFiles"
          label="Multiple Files"
          placeholder="Upload multiple files"
          multiple={true}
          {...inputProps}
        />
      )}
    />,
  );
};

// Helper function to simulate file selection
const simulateFileSelection = async (files: File[]) => {
  const user = userEvent.setup();
  const fileInput = screen.getByLabelText(/file/i, {
    selector: 'input[type="file"]',
  });

  await user.upload(fileInput, files);
};

describe('FormFileUpload', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Single File Mode', () => {
    it('renders with label and placeholder', () => {
      renderSingleFileUpload();

      expect(screen.getByLabelText('Single File')).toBeInTheDocument();
      expect(screen.getByText('Upload a single file')).toBeInTheDocument();
      expect(screen.getByText('Drop file here')).toBeInTheDocument();
    });

    it('renders empty state with upload button', () => {
      renderSingleFileUpload();

      const uploadButton = screen.getByRole('button');
      expect(uploadButton).toBeInTheDocument();
      expect(screen.getByText('Upload a single file')).toBeInTheDocument();
    });

    it('allows file selection through file input', async () => {
      renderSingleFileUpload();

      const mockFile = createMockFile('test.txt');
      await simulateFileSelection([mockFile]);

      expect(screen.getByText('test.txt')).toBeInTheDocument();
    });

    it('shows file details after selection', async () => {
      renderSingleFileUpload();

      const mockFile = createMockFile('document.pdf', 2048);
      await simulateFileSelection([mockFile]);

      expect(screen.getByText('document.pdf')).toBeInTheDocument();
      expect(screen.getByText('2048 bytes')).toBeInTheDocument();
    });

    it('allows removing selected file', async () => {
      renderSingleFileUpload();

      const mockFile = createMockFile('test.txt');
      await simulateFileSelection([mockFile]);

      expect(screen.getByText('test.txt')).toBeInTheDocument();

      // Find remove button by aria-label
      const removeButton = screen.getByLabelText('remove');

      await act(async () => {
        fireEvent.click(removeButton);
      });

      expect(screen.queryByText('test.txt')).not.toBeInTheDocument();
      expect(screen.getByText('Upload a single file')).toBeInTheDocument();
    });

    it('replaces file when new file is selected', async () => {
      renderSingleFileUpload();

      const firstFile = createMockFile('first.txt');
      const secondFile = createMockFile('second.txt');

      // Select first file
      await simulateFileSelection([firstFile]);
      expect(screen.getByText('first.txt')).toBeInTheDocument();

      // Select second file
      await simulateFileSelection([secondFile]);
      expect(screen.queryByText('first.txt')).not.toBeInTheDocument();
      expect(screen.getByText('second.txt')).toBeInTheDocument();
    });

    it('displays validation error when no file is selected', async () => {
      renderSingleFileUpload({
        showSubmitButton: true,
        submitButtonText: 'Submit',
      });

      await act(async () => {
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
      });

      expect(screen.getByText('File is required')).toBeInTheDocument();
    });

    it('handles file type validation with accept prop', async () => {
      renderSingleFileUpload({}, { accept: '.pdf' });

      const mockFile = createMockFile('test.pdf', 1024, 'application/pdf');
      await simulateFileSelection([mockFile]);

      expect(screen.getByText('test.pdf')).toBeInTheDocument();
    });
  });

  describe('Read-only Mode', () => {
    it('disables file selection when read-only', () => {
      renderSingleFileUpload({}, { isReadOnly: true });

      const fileInput = screen.getByLabelText(/file/i, {
        selector: 'input[type="file"]',
      });
      expect(fileInput).toHaveAttribute('readonly');
    });
  });

  describe('Validation', () => {
    it('validates file extensions correctly', async () => {
      renderSingleFileUpload({}, { accept: '.txt,.pdf' });

      const validFile = createMockFile('document.txt', 1024, 'text/plain');
      await simulateFileSelection([validFile]);

      expect(screen.getByText('document.txt')).toBeInTheDocument();
    });

    it('validates MIME types correctly', async () => {
      renderSingleFileUpload({}, { accept: 'image/*' });

      const validFile = createMockFile('image.jpg', 1024, 'image/jpeg');
      await simulateFileSelection([validFile]);

      expect(screen.getByText('image.jpg')).toBeInTheDocument();
    });

    it('prevents multiple file selection in single mode', async () => {
      renderSingleFileUpload();

      const mockFiles = [
        createMockFile('file1.txt'),
        createMockFile('file2.txt'),
      ];

      await simulateFileSelection(mockFiles);

      // Should only show the first file
      expect(screen.getByText('file1.txt')).toBeInTheDocument();
      expect(screen.queryByText('file2.txt')).not.toBeInTheDocument();
    });
  });
});
