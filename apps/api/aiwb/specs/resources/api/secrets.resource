# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for AIWB API secrets endpoints.
...                 Provides direct API operation wrappers for the /namespaces/{namespace}/secrets endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Resource            resources/api/common.resource


*** Keywords ***
AIWB Secrets Endpoint
    [Documentation]    Return the full secrets endpoint URL for a namespace.
    ...    Pattern: /namespaces/{namespace}/secrets
    [Arguments]    ${namespace}
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=namespaces/${namespace}/secrets
    RETURN    ${endpoint}

Create AIWB Secret
    [Documentation]    Create a new secret via AIWB API.
    ...
    ...    Args:
    ...    namespace (str): Kubernetes namespace
    ...    body (dict): Secret creation payload (name, data, use_case)
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response containing the created secret
    [Arguments]    ${namespace}    ${body}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    AIWB Secrets Endpoint    ${namespace}

    Log    POST ${endpoint}    DEBUG
    Log    Request body: ${body}    DEBUG

    ${response}=    Safe Post Request    ${endpoint}
    ...    json=${body}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}

List AIWB Secrets
    [Documentation]    List all secrets in a namespace via AIWB API.
    ...    Optionally filter by use_case query parameter.
    ...
    ...    Args:
    ...    namespace (str): Kubernetes namespace
    ...    use_case (str): Optional use_case filter
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response containing the list of secrets
    [Arguments]    ${namespace}    ${use_case}=${None}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    AIWB Secrets Endpoint    ${namespace}

    &{params}=    Create Dictionary
    IF    $use_case is not None
        Set To Dictionary    ${params}    use_case=${use_case}
    END

    Log    GET ${endpoint} params=${params}    DEBUG

    ${response}=    Safe Get Request    ${endpoint}
    ...    params=${params}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}

Get AIWB Secret
    [Documentation]    Get a specific secret by name via AIWB API.
    ...
    ...    Args:
    ...    namespace (str): Kubernetes namespace
    ...    secret_name (str): Name of the secret
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response containing the secret details
    [Arguments]    ${namespace}    ${secret_name}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    AIWB Secrets Endpoint    ${namespace}

    Log    GET ${endpoint}/${secret_name}    DEBUG

    ${response}=    Safe Get Request    ${endpoint}/${secret_name}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}

Delete AIWB Secret
    [Documentation]    Delete a secret by name via AIWB API.
    ...
    ...    Args:
    ...    namespace (str): Kubernetes namespace
    ...    secret_name (str): Name of the secret to delete
    ...    expected_status (int/str): Expected HTTP status code
    ...
    ...    Returns:
    ...    response: API response (204 No Content on success)
    [Arguments]    ${namespace}    ${secret_name}    ${expected_status}=any
    Create api session    aiwb

    ${endpoint}=    AIWB Secrets Endpoint    ${namespace}

    Log    DELETE ${endpoint}/${secret_name}    DEBUG

    ${response}=    Safe Delete Request    ${endpoint}/${secret_name}
    ...    expected_status=${expected_status}

    Log    Response status: ${response.status_code}    DEBUG

    RETURN    ${response}
