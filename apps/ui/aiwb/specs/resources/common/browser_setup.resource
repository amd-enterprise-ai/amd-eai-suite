# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Browser Library setup and teardown for UI E2E tests.
...                 Provides browser initialization and cleanup keywords.
Library             Browser    auto_closing_level=TEST    enable_presenter_mode=${FALSE}
Library             String


*** Variables ***
${BROWSER_TYPE}             chromium
${BROWSER_HEADLESS}         ${TRUE}
${BROWSER_TIMEOUT}          30s


*** Keywords ***
Open test browser
    [Documentation]    Opens a new browser with tracing enabled for UI testing.
    ...                Tracing captures DOM snapshots, network requests, and console logs
    ...                at each step. Traces are saved on failure for post-mortem debugging
    ...                via Playwright Trace Viewer (https://trace.playwright.dev/).
    New Browser    browser=${BROWSER_TYPE}    headless=${BROWSER_HEADLESS}
    New Context
    ...    viewport={'width': 1920, 'height': 1080}
    ...    ignoreHTTPSErrors=${TRUE}
    ...    tracing=on
    New Page
    Set Browser Timeout    ${BROWSER_TIMEOUT}

Close test browser
    [Documentation]    Takes screenshot on failure. Browser Library auto-closes context after each test
    ...                (auto_closing_level=TEST), which saves the Playwright trace automatically.
    ...                Trace files can be viewed at https://trace.playwright.dev/.
    IF    '${TEST STATUS}' == 'FAIL'
        ${safe_name}=    Replace String    ${TEST NAME}    ${SPACE}    _
        Take Screenshot    filename=${safe_name}
    END
