// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconCheck, IconCopy, IconDownload } from '@tabler/icons-react';
import { FC, memo, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import {
  oneDark,
  oneLight,
} from 'react-syntax-highlighter/dist/cjs/styles/prism';

import { useTranslation } from 'next-i18next';
import { useTheme } from 'next-themes';

import {
  generateRandomString,
  programmingLanguages,
} from '@/utils/app/codeblock';

interface Props {
  language: string;
  value: string;
  allowDownload?: boolean;
}

export const CodeBlock: FC<Props> = memo(
  ({ language, value, allowDownload = true }) => {
    const { t } = useTranslation('markdown');
    const { theme } = useTheme();
    const [isCopied, setIsCopied] = useState<Boolean>(false);

    const copyToClipboard = () => {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        return;
      }

      navigator.clipboard.writeText(value).then(() => {
        setIsCopied(true);

        setTimeout(() => {
          setIsCopied(false);
        }, 2000);
      });
    };
    const downloadAsFile = () => {
      const fileExtension = programmingLanguages[language] || '.file';
      const suggestedFileName = `file-${generateRandomString(
        3,
        true,
      )}${fileExtension}`;
      const fileName = window.prompt(
        t('Enter file name') || '',
        suggestedFileName,
      );

      if (!fileName) {
        // user pressed cancel on prompt
        return;
      }

      const blob = new Blob([value], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.download = fileName;
      link.href = url;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    };
    return (
      <div className="codeblock group relative font-sans text-base my-4 group">
        <div className="absolute group-hover:visible invisible rounded-md right-3 top-3 text-default-800 bg-default-100">
          <div className="flex items-center gap-1 text-sm font-light py-1 px-3">
            <button
              className="flex gap-1 items-center rounded bg-none hover:text-primary"
              onClick={copyToClipboard}
            >
              {isCopied ? (
                <>
                  <IconCheck
                    size={16}
                    stroke={2}
                    className="text-secondary rounded-full"
                  />
                  <span className="text-secondary">{t('Copied!')}</span>
                </>
              ) : (
                <>
                  <IconCopy size={16} stroke={2} />
                  {t('Copy')}
                </>
              )}
            </button>
            <div className="h-full w-px bg-default-900"></div>
            {allowDownload && (
              <button
                className="flex gap-1 items-center rounded bg-none hover:text-primary"
                onClick={downloadAsFile}
              >
                <IconDownload size={16} stroke={2} />{' '}
                <span>{t('Download')}</span>
              </button>
            )}
          </div>
        </div>

        <SyntaxHighlighter
          language={language}
          style={theme == 'dark' ? oneDark : oneLight}
          customStyle={{ margin: 0, fontSize: '0.8em' }}
        >
          {value}
        </SyntaxHighlighter>
      </div>
    );
  },
);
CodeBlock.displayName = 'CodeBlock';
