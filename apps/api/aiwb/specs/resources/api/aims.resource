# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Low-level keywords for Catalog API AIMs endpoints.
...                 Provides direct API operation wrappers for the /aims endpoints.
...                 This is part of the API layer that handles raw HTTP requests/responses.
Library             RequestsLibrary
Library             Collections
Library             BuiltIn
Resource            resources/api/common.resource


*** Keywords ***
AIMs endpoint
    [Documentation]    Return the full AIMs endpoint url
    ${endpoint}=            Service API Endpoint    aiwb    endpoint=cluster/aims/models
    RETURN                  ${endpoint}

AIM Services endpoint
    [Documentation]    Return the AIMServices endpoint url for a namespace
    [Arguments]             ${namespace}
    ${endpoint}=            Service API Endpoint    aiwb    endpoint=namespaces/${namespace}/aims/services
    RETURN                  ${endpoint}

Get AIM
    [Documentation]    Retrieve a specific AIM by resource name
    ...
    ...    Args:
    ...    resource_name (str): Kubernetes resource name of the AIMClusterModel
    ...
    ...    Return:
    ...    response: API response containing the AIM details
    [Arguments]             ${resource_name}        ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=            AIMs endpoint
    ${response}=            Safe Get Request        ${endpoint}/${resource_name}                    expected_status=${expected_status}
    RETURN                  ${response}

List AIMs
    [Documentation]    List all available AIMs (AIMClusterModels from Kubernetes)
    ...
    ...    Return:
    ...    response: API response containing list of AIMs
    [Arguments]             ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=            AIMs endpoint
    ${response}=            Safe Get Request        ${endpoint}             expected_status=${expected_status}
    RETURN                  ${response}

Deploy AIM
    [Documentation]    Deploy an AIM by creating an AIMService in a namespace
    ...
    ...    Args:
    ...    model (str): AIMClusterModel resource name (e.g., 'meta-llama-3-8b')
    ...    deploy_data (dict): Deployment configuration (replicas, hf_token, etc.)
    ...    namespace (str): Kubernetes namespace to deploy into
    ...
    ...    Return:
    ...    response: API response containing the AIMService details
    [Arguments]             ${model}                ${deploy_data}          ${namespace}            ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=            AIM Services endpoint   ${namespace}
    # Add model name to deploy data
    ${full_deploy_data}=    Create Dictionary       model=${model}
    Set To Dictionary       ${full_deploy_data}     &{deploy_data}
    ${response}=            Safe Post Request       ${endpoint}             json=${full_deploy_data}                        expected_status=${expected_status}
    RETURN                  ${response}

Undeploy AIM
    [Documentation]    Undeploy an AIM by deleting its AIMService from a namespace
    ...
    ...    Args:
    ...    service_id (str): UUID of the AIMService to undeploy
    ...    namespace (str): Kubernetes namespace where AIM is deployed
    ...
    ...    Return:
    ...    response: API response
    [Arguments]             ${service_id}           ${namespace}            ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=            AIM Services endpoint   ${namespace}
    ${response}=            Safe Delete Request     ${endpoint}/${service_id}                       expected_status=${expected_status}
    RETURN                  ${response}

List AIM Services
    [Documentation]    List deployed AIMServices in a namespace
    ...
    ...    Args:
    ...    namespace (str): Kubernetes namespace to list services from
    ...
    ...    Return:
    ...    response: API response containing list of AIMServices
    [Arguments]             ${namespace}            ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=            AIM Services endpoint   ${namespace}
    ${response}=            Safe Get Request        ${endpoint}             expected_status=${expected_status}
    RETURN                  ${response}

Get AIM Service
    [Documentation]    Get a specific AIMService by ID
    ...
    ...    Args:
    ...    service_id (str): UUID of the AIMService
    ...    namespace (str): Kubernetes namespace
    ...
    ...    Return:
    ...    response: API response containing the AIMService details
    [Arguments]             ${service_id}           ${namespace}            ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=            AIM Services endpoint   ${namespace}
    ${response}=            Safe Get Request        ${endpoint}/${service_id}                       expected_status=${expected_status}
    RETURN                  ${response}

List AIM Templates
    [Documentation]    List AIM cluster service templates for a given model
    ...
    ...    Args:
    ...    aim_resource_name (str): AIMClusterModel resource name to get templates for
    ...
    ...    Return:
    ...    response: API response containing list of AIMClusterServiceTemplates
    [Arguments]             ${aim_resource_name}    ${expected_status}=any
    Create api session    aiwb
    ${endpoint}=            Service API Endpoint    aiwb    endpoint=cluster/aims/templates
    ${params}=              Create Dictionary       aim_resource_name=${aim_resource_name}
    ${response}=            Safe Get Request        ${endpoint}             params=${params}        expected_status=${expected_status}
    RETURN                  ${response}
