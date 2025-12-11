# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level common API testing utilities.
...                 Provides base functionality for constructing API URLs and other
...                 shared utilities used by specific API endpoint resources.
...                 This is the lowest layer of the testing hierarchy.
Resource            ../catalog_keywords.resource
Resource            ../test_data.resource
Resource            ../authorization.resource
Resource            ../deployment.resource
Library             RequestsLibrary


*** Variables ***
${API_SESSION}          ${None}
# Removed: ${CATALOG_ENDPOINT} - endpoint resolution delegated to KubeConnection.py cache
${SESSION_TOKEN_REFRESH_INTERVAL}    240    # Refresh session token every 4 minutes (240s)
${SESSION_LAST_REFRESH}    ${None}    # Timestamp of last session token refresh


*** Keywords ***
Catalog endpoint
    [Documentation]    Returns the full endpoint url for a catalog api endpoint.
    ...                Endpoint resolution and caching is handled by KubeConnection.py,
    ...                which includes automatic port forward validation and recovery.
    [Arguments]             ${endpoint}=${None}

    # Always resolve endpoint - KubeConnection.py handles caching + validation
    ${base_url}=            Service endpoint        airm                    airm-api

    IF    $endpoint is not None
        RETURN                  ${base_url}/v1/${endpoint}
    END
    RETURN                  ${base_url}/v1

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

    # If session already exists, ensure it has a fresh token
    IF    $API_SESSION is not None
        Log                     API session exists, ensuring fresh token    DEBUG
        Ensure Fresh Session Token
        RETURN
    END

    # Create new session with improved connection handling
    Log                     Creating API session    INFO
    ${base_url}=            Catalog endpoint
    Log                     Base URL: ${base_url}    DEBUG
    ${access_token} =       Authorization token
    &{headers} =            Create dictionary
    ...                     Content-Type=application/json
    ...                     Authorization=Bearer ${access_token}
    ...                     Connection=close
    Log                     Session headers configured (token length: ${access_token.__len__()})    DEBUG

    # Create session with improved settings for connection stability
    Create session          catalog_api             ${base_url}             headers=${headers}
    ...                     verify=False            timeout=30              max_retries=3

    Set suite variable      ${API_SESSION}          catalog_api

    # Track when we created/refreshed the session
    ${current_time} =       Get Current Date
    Set Suite Variable      ${SESSION_LAST_REFRESH}    ${current_time}
    Log                     API session created successfully with improved connection settings    DEBUG

Recreate api session
    [Documentation]    Forces recreation of the API session with a fresh token
    ...    Use this after operations that change user group membership (e.g., adding user to project)
    ...    as the JWT token contains group claims that need to be refreshed
    Log                     Recreating API session with fresh token    INFO
    Set suite variable      ${API_SESSION}          ${None}
    TRY
        Set Global Variable    ${AUTH_TOKEN}    ${None}
        Set Global Variable    ${TOKEN_TIMESTAMP}    ${None}
        Log                     Cleared cached authorization tokens    DEBUG
    EXCEPT
        Log                     No global token variables to clear    DEBUG
    END
    Create api session
    Log                     API session recreated successfully    DEBUG

Log Current User Groups
    [Documentation]    Queries the /v1/user_groups endpoint and logs the response.
    Create api session
    ${endpoint}=            Set Variable            /v1/user_groups
    Log                     GET ${endpoint}    DEBUG
    TRY
        ${response}=            Get On Session          ${API_SESSION}          ${endpoint}             expected_status=any
        Log                     User groups response status: ${response.status_code}    DEBUG
        Log To Console          \nUser Groups Response (Status: ${response.status_code}):\n${response.text}\n
    EXCEPT    HTTPError    AS    ${error}
        Log                     Failed to get user groups: ${error}    ERROR
        Log To Console          ERROR: Failed to get user groups: ${error}
    END

Ensure Port Forward Alive
    [Documentation]    Validates that port forwarding is alive and recreates it if necessary.
    ...
    ...                **Purpose**:
    ...                This keyword ensures the kubectl port forward connection is still active
    ...                before making HTTP requests. If the cached port forward has died, it
    ...                automatically creates a new one with a fresh random port.
    ...
    ...                **Implementation**:
    ...                - Calls `Catalog endpoint` which delegates to `Service endpoint` (deployment.resource)
    ...                - Service endpoint uses KubeConnection.py for port forward management
    ...                - KubeConnection.py validates cached ports are still accessible
    ...                - If validation fails, creates new port forward automatically
    ...                - No session updates needed - Create api session handles URL setup
    ...
    ...                **When to Use**:
    ...                This is called automatically by all Safe HTTP Request wrapper keywords
    ...                (Safe Get Request, Safe Post Request, etc.). You should NOT need to
    ...                call this directly in test code.
    ...
    ...                **Connection Resilience**:
    ...                Port forwarding can die during long test runs due to network issues,
    ...                kubectl process crashes, or timeout. This mechanism ensures tests
    ...                survive port forwarding failures transparently without manual intervention.
    ...
    ...                **Note**:
    ...                Currently this keyword just validates the port forward exists via Catalog endpoint.
    ...                The actual resilience comes from Create api session being called before each
    ...                resource operation, which gets the current port forward URL from KubeConnection.

    # Validate/recreate port forward - KubeConnection.py handles caching and validation
    # This call ensures the port forward is alive and will create a new one if needed
    ${base_url}=            Catalog endpoint

    # Log for debugging
    Log                     Port forward validated: ${base_url}    DEBUG

Safe Get Request
    [Documentation]    Execute GET request with automatic port forward recovery.
    ...
    ...                **Port Forwarding Resilience**:
    ...                This keyword wraps RequestsLibrary's `Get On Session` with automatic
    ...                port forward validation and recovery. Before each request, it ensures
    ...                the kubectl port forward is alive and recreates it if necessary.
    ...
    ...                **Usage**:
    ...                Use this instead of `Get On Session` in resource file keywords:
    ...                | ${response}=    Safe Get Request    ${endpoint}    expected_status=200
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Get On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    # Ensure port forward is alive before making request
    Ensure Port Forward Alive

    # Execute actual GET request with all original arguments
    ${response}=            Get On Session          ${API_SESSION}          ${endpoint}             &{kwargs}
    RETURN                  ${response}

Safe Post Request
    [Documentation]    Execute POST request with automatic port forward recovery.
    ...
    ...                **Port Forwarding Resilience**:
    ...                This keyword wraps RequestsLibrary's `Post On Session` with automatic
    ...                port forward validation and recovery. Before each request, it ensures
    ...                the kubectl port forward is alive and recreates it if necessary.
    ...
    ...                **Usage**:
    ...                Use this instead of `Post On Session` in resource file keywords:
    ...                | ${response}=    Safe Post Request    ${endpoint}    json=${data}    expected_status=201
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Post On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    # Ensure port forward is alive before making request
    Ensure Port Forward Alive

    # Execute actual POST request with all original arguments
    ${response}=            Post On Session         ${API_SESSION}          ${endpoint}             &{kwargs}
    RETURN                  ${response}

Safe Put Request
    [Documentation]    Execute PUT request with automatic port forward recovery.
    ...
    ...                **Port Forwarding Resilience**:
    ...                This keyword wraps RequestsLibrary's `Put On Session` with automatic
    ...                port forward validation and recovery. Before each request, it ensures
    ...                the kubectl port forward is alive and recreates it if necessary.
    ...
    ...                **Usage**:
    ...                Use this instead of `Put On Session` in resource file keywords:
    ...                | ${response}=    Safe Put Request    ${endpoint}    json=${data}    expected_status=200
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Put On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    # Ensure port forward is alive before making request
    Ensure Port Forward Alive

    # Execute actual PUT request with all original arguments
    ${response}=            Put On Session          ${API_SESSION}          ${endpoint}             &{kwargs}
    RETURN                  ${response}

Safe Delete Request
    [Documentation]    Execute DELETE request with automatic port forward recovery.
    ...
    ...                **Port Forwarding Resilience**:
    ...                This keyword wraps RequestsLibrary's `Delete On Session` with automatic
    ...                port forward validation and recovery. Before each request, it ensures
    ...                the kubectl port forward is alive and recreates it if necessary.
    ...
    ...                **Usage**:
    ...                Use this instead of `Delete On Session` in resource file keywords:
    ...                | ${response}=    Safe Delete Request    ${endpoint}    expected_status=204
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Delete On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    # Ensure port forward is alive before making request
    Ensure Port Forward Alive

    # Execute actual DELETE request with all original arguments
    ${response}=            Delete On Session       ${API_SESSION}          ${endpoint}             &{kwargs}
    RETURN                  ${response}

Safe Patch Request
    [Documentation]    Execute PATCH request with automatic port forward recovery.
    ...
    ...                **Port Forwarding Resilience**:
    ...                This keyword wraps RequestsLibrary's `Patch On Session` with automatic
    ...                port forward validation and recovery. Before each request, it ensures
    ...                the kubectl port forward is alive and recreates it if necessary.
    ...
    ...                **Usage**:
    ...                Use this instead of `Patch On Session` in resource file keywords:
    ...                | ${response}=    Safe Patch Request    ${endpoint}    json=${data}    expected_status=200
    ...
    ...                **Arguments**:
    ...                All arguments are passed through to `Patch On Session` exactly as-is.
    ...                See RequestsLibrary documentation for full parameter details.
    [Arguments]             ${endpoint}             &{kwargs}

    # Ensure port forward is alive before making request
    Ensure Port Forward Alive

    # Execute actual PATCH request with all original arguments
    ${response}=            Patch On Session        ${API_SESSION}          ${endpoint}             &{kwargs}
    RETURN                  ${response}
