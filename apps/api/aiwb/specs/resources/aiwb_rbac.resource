# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       Business-logic keywords for AIWB API RBAC testing.
...                 Builds on the team-member session infrastructure from `airm_rbac.resource`
...                 (AIRM-side, since team-member roles and project membership are AIRM concepts)
...                 to test AIWB endpoints under a non-admin identity.
...
...                 Why import an AIRM resource? AIWB endpoints accept the same Keycloak SSO token
...                 as AIRM, so reusing AIRM's session-switching avoids duplicating credential
...                 handling. The AIWB pythonpath includes `airm/specs`, making this import safe
...                 and ownership-correct: the AIRM-owned infrastructure stays in AIRM specs;
...                 only AIWB-specific keywords live here.
Resource            resources/airm_rbac.resource
Resource            resources/api/common.resource


*** Keywords ***
Team member lists AIM services for project namespace "${namespace}"
    [Documentation]    Lists inference deployments in a project namespace as the team member.
    ...    Calls the AIWB inference capability API (/v1/projects/{project}/inference).
    ...    The team member Bearer token is valid across services because Keycloak issues
    ...    a single SSO token, so the AIRM-bound session can call AIWB endpoints by passing
    ...    an absolute URL.
    ...    Sets: TEST_RESPONSE
    Switch to team member session
    ${endpoint}=    Service API Endpoint    aiwb    endpoint=projects/${namespace}/inference
    ${response}=    Safe Get Request    ${endpoint}    expected_status=any
    Set Test Variable    ${TEST_RESPONSE}    ${response}
    Switch to admin session
    RETURN    ${response}

Response should contain AIM service list
    [Documentation]    Verifies the response is the standard AIWB list envelope.
    ...    The list may be empty -- this test only verifies access is permitted, not that
    ...    the team member's project has AIM services deployed.
    ${json}=    Set Variable    ${TEST_RESPONSE.json()}
    Dictionary Should Contain Key    ${json}    data
    ${data}=    Get From Dictionary    ${json}    data
    Should Be True    isinstance($data, list)    msg=Expected 'data' field to be a list
    Log    AIM services list returned with ${{len($data)}} entries    INFO
