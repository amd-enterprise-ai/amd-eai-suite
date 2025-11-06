// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import { BaseStatusDisplay } from '@/components/shared/Status';

describe('BaseStatus', () => {
  it('renders created status with check icon and correct label', () => {
    act(() => {
      render(
        <BaseStatusDisplay
          statusPrefix="secretStatus"
          translationNamespace="secrets"
          status={'Synced'}
          statusReason={null}
          statusIconMap={{
            Synced: <svg data-testid="icon-check" />,
          }}
          hasErrors={false}
        />,
      );
    });
    expect(screen.getByTestId('icon-check')).toBeInTheDocument();
    expect(screen.getByText(`secretStatus.Synced`)).toBeInTheDocument();
  });

  it('renders no status text if specified in statusesToHide', () => {
    act(() => {
      render(
        <BaseStatusDisplay
          statusPrefix="secretStatus"
          translationNamespace="secrets"
          status={'Synced'}
          statusReason={null}
          statusIconMap={{
            Synced: <svg data-testid="icon-check" />,
          }}
          hasErrors={false}
          statusesToHide={['Synced']}
        />,
      );
    });
    expect(screen.getByTestId('icon-check')).toBeInTheDocument();
    expect(screen.queryByText(`secretStatus.Synced`)).not.toBeInTheDocument();
  });

  it('renders error message if hasError is set', () => {
    act(() => {
      render(
        <BaseStatusDisplay
          statusPrefix="secretStatus"
          translationNamespace="secrets"
          status={'Failed'}
          statusReason={'Some error'}
          statusIconMap={{
            Failed: <svg data-testid="icon-error" />,
          }}
          hasErrors={true}
        />,
      );
    });
    expect(screen.getByTestId('icon-error')).toBeInTheDocument();
    expect(screen.getByText(`secretStatus.Failed`)).toBeInTheDocument();

    const errorMessageTrigger = screen.getByText(
      '(statusReason.messageTrigger)',
    );
    expect(errorMessageTrigger).toBeInTheDocument();
    fireEvent.click(errorMessageTrigger);
    expect(screen.getByText('Some error')).toBeInTheDocument();
  });

  it('error trigger not rendered, if hasError is not set', () => {
    act(() => {
      render(
        <BaseStatusDisplay
          statusPrefix="secretStatus"
          translationNamespace="secrets"
          status={'Failed'}
          statusReason={'Some error'}
          statusIconMap={{
            Failed: <svg data-testid="icon-error" />,
          }}
          hasErrors={false}
        />,
      );
    });
    expect(screen.getByTestId('icon-error')).toBeInTheDocument();
    expect(screen.getByText(`secretStatus.Failed`)).toBeInTheDocument();

    const errorMessageTrigger = screen.queryByText(
      '(statusReason.messageTrigger)',
    );
    expect(errorMessageTrigger).not.toBeInTheDocument();
  });

  it('renders error message with secondary error messages', () => {
    act(() => {
      render(
        <BaseStatusDisplay
          statusPrefix="secretStatus"
          translationNamespace="secrets"
          status={'Failed'}
          statusReason={'Primary error reason'}
          statusIconMap={{
            Failed: <svg data-testid="icon-error" />,
          }}
          secondaryStatusReason={[
            { key: 'key-1', description: 'secondary error 1' },
            { key: 'key-2', description: 'secondary error 2' },
          ]}
          hasErrors={true}
        />,
      );
    });
    expect(screen.getByTestId('icon-error')).toBeInTheDocument();
    expect(screen.getByText(`secretStatus.Failed`)).toBeInTheDocument();

    const errorMessageTrigger = screen.getByText(
      '(statusReason.messageTrigger)',
    );
    expect(errorMessageTrigger).toBeInTheDocument();
    fireEvent.click(errorMessageTrigger);

    expect(screen.getByText('Primary error reason')).toBeInTheDocument();

    expect(screen.getByText('status.errorDetail.title')).toBeInTheDocument();
    expect(screen.queryByText('secondary error 1')).toBeInTheDocument();

    expect(screen.queryByText('key-1')).toBeInTheDocument();

    expect(screen.queryByText('secondary error 2')).not.toBeInTheDocument();

    const nextErrorButton = screen.getByLabelText(
      'status.errorDetail.action.next',
    );

    expect(nextErrorButton).toBeInTheDocument();

    fireEvent.click(nextErrorButton);

    expect(screen.queryByText('key-2')).toBeInTheDocument();

    expect(screen.queryByText('secondary error 1')).not.toBeInTheDocument();
    expect(screen.queryByText('secondary error 2')).toBeInTheDocument();
  });
});
