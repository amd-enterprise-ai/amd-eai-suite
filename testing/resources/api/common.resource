# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level common API testing utilities.
...                 Provides base functionality for constructing API URLs and other
...                 shared utilities used by specific API endpoint resources.
...                 This is the lowest layer of the testing hierarchy.
Resource            ../authorization.resource
Resource            endpoints.resource
Resource            ../common/response_assertions.resource
Library             RequestsLibrary
Library             Collections


*** Variables ***
${API_SESSION}          ${None}
${SESSION_SERVICE_NAME}    ${None}    # Which service the current session is for
${SESSION_TOKEN_REFRESH_INTERVAL}    240    # Refresh session token every 4 minutes (240s)
${SESSION_LAST_REFRESH}    ${None}    # Timestamp of last session token refresh
${USING_EXTERNAL_ENDPOINT}    ${FALSE}    # Track if using external endpoint (True) or port-forward (False)


*** Keywords ***
Ensure Fresh Session Token
    [Documentation]    Ensures the API session has a fresh authorization token.
    ...                Checks session age and only refreshes if older than SESSION_TOKEN_REFRESH_INTERVAL.
    ...                This is called internally by Create api session before every API request.

    # If no session exists yet, nothing to refresh
    IF    $API_SESSION is None
        RETURN
    END

    # Check if we need to refresh based on session age
    ${current_time} =       Get Current Date
    ${should_refresh} =     Set Variable    ${True}

    IF    $SESSION_LAST_REFRESH is not None
        ${time_diff} =          Subtract Date From Date    ${current_time}    ${SESSION_LAST_REFRESH}
        IF    ${time_diff} < ${SESSION_TOKEN_REFRESH_INTERVAL}
            ${should_refresh} =     Set Variable    ${False}
            Log                     Session token still fresh (age: ${time_diff}s, refresh interval: ${SESSION_TOKEN_REFRESH_INTERVAL}s)    TRACE
        ELSE
            Log                     Session token needs refresh (age: ${time_diff}s, refresh interval: ${SESSION_TOKEN_REFRESH_INTERVAL}s)    DEBUG
        END
    ELSE
        Log                     No session refresh timestamp, forcing refresh    DEBUG
    END

    # Only refresh if needed
    IF    ${should_refresh}
        # Get token from KubeconfigAuth (uses its own 55-minute cache)
        ${fresh_token} =        Authorization token

        # Update the session Authorization header
        &{headers} =            Create Dictionary       Authorization=Bearer ${fresh_token}
        Update Session          ${API_SESSION}          headers=${headers}

        # Track when we refreshed the session
        Set Suite Variable      ${SESSION_LAST_REFRESH}    ${current_time}
        Log                     Session token refreshed (token length: ${fresh_token.__len__()})    DEBUG
    END

Create api session
    [Documentation]    Creates a session to the API if it doesn't exist, or ensures existing session has fresh token.
    ...                The session is automatically refreshed with a new token if it already exists,
    ...                ensuring long-running test suites don't encounter 401 authentication errors.
    ...
    ...                Args:
    ...                - service_name: Service identifier (e.g., "airm", "aiwb")
    [Arguments]    ${service_name}

    # If session already exists, ensure it has a fresh token
    IF    $API_SESSION is not None
        Log                     API session exists, ensuring fresh token    DEBUG
        Ensure Fresh Session Token
        RETURN
    END

    # Create new session with improved connection handling
    Log                     Creating ${service_name} API session    INFO
    ${base_url}=            Service API Endpoint    ${service_name}
    Log                     Base URL: ${base_url}    DEBUG
    ${access_token} =       Authorization token
    &{headers} =            Create dictionary
    ...                     Content-Type=application/json
    ...                     Authorization=Bearer ${access_token}
    ...                     Connection=close
    Log                     Session headers configured (token length: ${access_token.__len__()})    DEBUG

    # Create session with improved settings for connection stability
    ${session_alias}=       Set Variable            ${service_name}_api
    Create session          ${session_alias}        ${base_url}             headers=${headers}
    ...                     verify=False            timeout=30              max_retries=3

    Set suite variable      ${API_SESSION}          ${session_alias}
    Set suite variable      ${SESSION_SERVICE_NAME}    ${service_name}

    # Track when we created/refreshed the session
    ${current_time} =       Get Current Date
    Set Suite Variable      ${SESSION_LAST_REFRESH}    ${current_time}
    Log                     API session created for ${service_name} with improved connection settings    DEBUG

Recreate api session
    [Documentation]    Forces recreation of the API session with a fresh token.
    ...    Use this after operations that change user group membership (e.g., adding user to project)
    ...    as the JWT token contains group claims that need to be refreshed.
    ...    Uses the service name from the previous session if not explicitly provided.

    # Remember the service name before clearing the session
    ${service}=             Set Variable            ${SESSION_SERVICE_NAME}
    IF    $service is None
        Fail    Cannot recreate API session: no previous session exists. Call "Create api session" first.
    END

    Log                     Recreating ${service} API session with fresh token    INFO
    Set suite variable      ${API_SESSION}          ${None}
    TRY
        Set Global Variable    ${AUTH_TOKEN}    ${None}
        Set Global Variable    ${TOKEN_TIMESTAMP}    ${None}
        Log                     Cleared cached authorization tokens    DEBUG
    EXCEPT
        Log                     No global token variables to clear    DEBUG
    END
    Create api session    ${service}
    Log                     API session recreated successfully for ${service}    DEBUG

Ensure Port Forward Alive
    [Documentation]    Validates that port forwarding is alive (only when using port forwarding).
    ...                Skips validation when using external HTTPS endpoints.
    ...                Uses the service name from the current session to resolve the correct port-forward.

    # Skip validation if using external endpoints
    IF    ${USING_EXTERNAL_ENDPOINT}
        Log    Using external endpoint, skipping port forward validation    DEBUG
        RETURN
    END

    # Validate/recreate port forward for the current service
    IF    $SESSION_SERVICE_NAME is None
        Log    No active session, skipping port forward validation    DEBUG
        RETURN
    END
    ${base_url}=    Service API Endpoint    ${SESSION_SERVICE_NAME}
    Log    Port forward validated for ${SESSION_SERVICE_NAME}: ${base_url}    DEBUG

Safe Get Request
    [Documentation]    Execute GET request with automatic session management.
    ...
    ...                **Endpoint Resolution**:
    ...                This keyword wraps RequestsLibrary's `Get On Session`. The endpoint
    ...                (external or port-forward) is resolved once during session creation.
    ...                Port forward validation happens on-demand only when needed.
    ...
    ...                **Usage**:
    ...                Use this instead of `Get On Session` in resource file keywords:
    ...                | ${response}=    Safe Get Request    ${endpoint}    expected_status=200
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Get On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    # Ensure port forward is alive before making request (no-op for external endpoints)
    Ensure Port Forward Alive

    ${expected}=            Pop From Dictionary     ${kwargs}    expected_status    default=any
    ${response}=            Get On Session          ${API_SESSION}          ${endpoint}             expected_status=any    &{kwargs}
    Assert Expected Status    ${response}    ${expected}
    RETURN                  ${response}

Safe Post Request
    [Documentation]    Execute POST request with automatic session management.
    ...
    ...                **Endpoint Resolution**:
    ...                This keyword wraps RequestsLibrary's `Post On Session`. The endpoint
    ...                (external or port-forward) is resolved once during session creation.
    ...                Port forward validation happens on-demand only when needed.
    ...
    ...                **Usage**:
    ...                Use this instead of `Post On Session` in resource file keywords:
    ...                | ${response}=    Safe Post Request    ${endpoint}    json=${data}    expected_status=201
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Post On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    ${expected}=            Pop From Dictionary     ${kwargs}    expected_status    default=any
    ${response}=            Post On Session         ${API_SESSION}          ${endpoint}             expected_status=any    &{kwargs}
    Assert Expected Status    ${response}    ${expected}
    RETURN                  ${response}

Safe Put Request
    [Documentation]    Execute PUT request with automatic session management.
    ...
    ...                **Endpoint Resolution**:
    ...                This keyword wraps RequestsLibrary's `Put On Session`. The endpoint
    ...                (external or port-forward) is resolved once during session creation.
    ...                Port forward validation happens on-demand only when needed.
    ...
    ...                **Usage**:
    ...                Use this instead of `Put On Session` in resource file keywords:
    ...                | ${response}=    Safe Put Request    ${endpoint}    json=${data}    expected_status=200
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Put On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    ${expected}=            Pop From Dictionary     ${kwargs}    expected_status    default=any
    ${response}=            Put On Session          ${API_SESSION}          ${endpoint}             expected_status=any    &{kwargs}
    Assert Expected Status    ${response}    ${expected}
    RETURN                  ${response}

Safe Delete Request
    [Documentation]    Execute DELETE request with automatic session management.
    ...
    ...                **Endpoint Resolution**:
    ...                This keyword wraps RequestsLibrary's `Delete On Session`. The endpoint
    ...                (external or port-forward) is resolved once during session creation.
    ...                Port forward validation happens on-demand only when needed.
    ...
    ...                **Usage**:
    ...                Use this instead of `Delete On Session` in resource file keywords:
    ...                | ${response}=    Safe Delete Request    ${endpoint}    expected_status=204
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Delete On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    ${expected}=            Pop From Dictionary     ${kwargs}    expected_status    default=any
    ${response}=            Delete On Session       ${API_SESSION}          ${endpoint}             expected_status=any    &{kwargs}
    Assert Expected Status    ${response}    ${expected}
    RETURN                  ${response}

Safe Patch Request
    [Documentation]    Execute PATCH request with automatic session management.
    ...
    ...                **Endpoint Resolution**:
    ...                This keyword wraps RequestsLibrary's `Patch On Session`. The endpoint
    ...                (external or port-forward) is resolved once during session creation.
    ...                Port forward validation happens on-demand only when needed.
    ...
    ...                **Usage**:
    ...                Use this instead of `Patch On Session` in resource file keywords:
    ...                | ${response}=    Safe Patch Request    ${endpoint}    json=${data}    expected_status=200
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Patch On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    ${expected}=            Pop From Dictionary     ${kwargs}    expected_status    default=any
    ${response}=            Patch On Session        ${API_SESSION}          ${endpoint}             expected_status=any    &{kwargs}
    Assert Expected Status    ${response}    ${expected}
    RETURN                  ${response}

Assert Expected Status
    [Documentation]    Validates HTTP response status and fails with the response body on mismatch.
    ...    Extracts the error message from JSON responses (detail or error fields).
    [Arguments]    ${response}    ${expected_status}
    IF    "${expected_status}" == "any"    RETURN
    IF    ${response.status_code} != ${expected_status}
        ${message}=    Evaluate    __import__('json').loads($response.text).get('detail', __import__('json').loads($response.text).get('error', $response.text)) if $response.text.strip().startswith('{') else $response.text
        FAIL    ${message} (expected ${expected_status}, got ${response.status_code})
    END
