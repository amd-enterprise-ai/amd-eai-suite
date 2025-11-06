# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level cluster testing keywords.
...                 Provides business-logic level keywords for testing cluster operations.
...                 Uses the low-level API keywords from api/clusters.resource to implement
Resource            test_data.resource
Resource            api/clusters.resource
Library             Collections
Library             String
Library             OperatingSystem


*** Variables ***
${CURRENT_CLUSTER_ID}       ${None}


*** Keywords ***
Cluster exists in system
    [Documentation]    Ensures a cluster exists and sets its ID as a test variable.
    ...    Fetches the list of clusters and uses the ID of the first one found.
    ${response}=            Get clusters            expected_status=200
    ${clusters_list_obj}=                           Set Variable            ${response.json()['clusters']}
    ${clusters_list}=       Evaluate                list(${clusters_list_obj})

    IF    len($clusters_list) == 0
        FAIL                    No clusters found in the system. Cannot proceed with tests.
    END

    ${first_cluster}=       Get From List           ${clusters_list}        0
    Set Test Variable       ${CURRENT_CLUSTER_ID}                           ${first_cluster['id']}
    Log                     Using Cluster ID: ${CURRENT_CLUSTER_ID}
    # Optional: Verify the chosen cluster actually exists (redundant if List clusters worked)
    # ${verify_response}=    Get cluster    ${CURRENT_CLUSTER_ID}    expected_status=200
    Cluster ID query params                         ${CURRENT_CLUSTER_ID}

Cluster ID query params
    [Documentation]    Sets the cluster ID as a query parameter for the model creation request
    [Arguments]             ${cluster_id_arg}
    ${query_params}=        Create Dictionary       cluster_id=${cluster_id_arg}
    Set Test Variable       ${QUERY_PARAMS}         ${query_params}
