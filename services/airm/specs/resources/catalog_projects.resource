# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

*** Settings ***
Documentation       High-level project testing keywords.
...                 Provides business-logic level keywords for testing project operations.
...                 Uses the low-level API keywords from api/projects.resource to implement
Resource            test_data.resource
Resource            api/projects.resource
Resource            api/clusters.resource
Library             Collections
Library             String
Library             OperatingSystem
Library             ${CURDIR}/../libraries/KeycloakAuth.py


*** Variables ***
${CURRENT_PROJECT_ID}       ${None}
${CURRENT_PROJECT_NAME}     ${None}
${CURRENT_PROJECT_SLUG}     ${None}


*** Keywords ***
Project exists in system
    [Documentation]    Ensures the "e2e-testing" project exists and sets its ID as a test variable.
    ...    Fetches the list of projects and looks for the "e2e-testing" project specifically.
    ...    If the project doesn't exist, creates it automatically.
    ${response}=            Get projects            expected_status=200
    ${projects_list_obj}=                           Set Variable            ${response.json()['projects']}
    ${projects_list}=       Evaluate                list(${projects_list_obj})

    IF    len($projects_list) == 0
        Log                     No projects found in the system. Will create the e2e-testing project.
    END

    # Look for the "e2e-testing" project specifically
    ${e2e_project}=         Set Variable            ${None}
    FOR    ${project}    IN    @{projects_list}
        IF    '${project['name']}' == 'e2e-testing'
            ${e2e_project}=         Set Variable            ${project}
            BREAK
        END
    END

    IF    $e2e_project is None
        ${project_names}=       Evaluate                [p['name'] for p in $projects_list]
        Log                     e2e-testing project not found in system. Available projects: ${project_names}
        Log                     Creating e2e-testing project automatically...
        ${e2e_project}=         Create e2e testing project
    ELSE
        Log                     Found existing e2e-testing project with ID: ${e2e_project['id']}
        Ensure user is member of project                ${e2e_project['id']}
    END

    Set Test Variable       ${CURRENT_PROJECT_ID}                           ${e2e_project['id']}
    Set Test Variable       ${CURRENT_PROJECT_NAME}                         ${e2e_project['name']}
    ${project_slug}=        Slugify project name    ${e2e_project['name']}
    Set Test Variable       ${CURRENT_PROJECT_SLUG}                         ${project_slug}
    Log                     Using Project ID: ${CURRENT_PROJECT_ID}
    Log                     Using Project Name: ${CURRENT_PROJECT_NAME}
    Log                     Using Project Slug: ${CURRENT_PROJECT_SLUG}
    # Optional: Verify the chosen project actually exists (redundant if List projects worked)
    # ${verify_response}=    Get project    ${CURRENT_PROJECT_ID}    expected_status=200
    Project ID query params                         ${CURRENT_PROJECT_ID}

Project ID query params
    [Documentation]    Sets the project ID as a query parameter for requests
    [Arguments]             ${project_id_arg}
    ${query_params}=        Create Dictionary       project_id=${project_id_arg}
    Set Test Variable       ${QUERY_PARAMS}         ${query_params}

Slugify project name
    [Documentation]    Converts project name to a slug format (lowercase, replace spaces and special chars with hyphens)
    [Arguments]             ${project_name}
    ${slug}=                Replace String          ${project_name}         ${SPACE}                -
    ${slug}=                Convert To Lower Case                           ${slug}
    # Remove any other special characters that might cause issues
    ${slug}=                Replace String Using Regexp                     ${slug}                 [^a-z0-9-]              -
    RETURN                  ${slug}

Get current user
    [Documentation]    Get the current user information from the system by extracting email from JWT token.
    ...    CI service account has Platform Administrator privileges to access the users endpoint.
    Create API Session

    # Extract email from JWT token
    ${jwt_email}=           Get current user email from JWT

    # Get all users - CI service account has Platform Administrator privileges to access this endpoint
    ${users_endpoint}=      Catalog endpoint        users
    ${users_response}=      GET On Session          ${API_SESSION}          ${users_endpoint}       expected_status=200
    ${users_data}=          Set Variable            ${users_response.json()}
    ${users}=               Set Variable            ${users_data['users']}

    # Match the user by email from the JWT token
    ${current_user}=        Set Variable            ${None}

    FOR    ${user}    IN    @{users}
        IF    '${user['email']}' == '${jwt_email}'
            ${current_user}=        Set Variable            ${user}
            BREAK
        END
    END

    IF    $current_user is not None
        Log                     Found current user: ${current_user['email']} (ID: ${current_user['id']})
        RETURN                  ${current_user}
    ELSE
        FAIL                    JWT email ${jwt_email} not found in system users. Cannot identify current user.
    END

Get current user email from JWT
    [Documentation]    Extract email from the Authorization token (JWT) using Python library
    ${token}=               Authorization token
    ${email}=               Get Jwt Email From Token                        ${token}
    RETURN                  ${email}

Create e2e testing project
    [Documentation]    Creates the "e2e-testing" project with minimal quota requirements.
    ...    Uses the same cluster as an existing project to ensure it's healthy.

    # Get existing projects to find a cluster that's already in use (and therefore healthy)
    ${projects_response}=                           Get projects            expected_status=200
    ${existing_projects}=                           Set Variable            ${projects_response.json()['projects']}

    IF    len($existing_projects) == 0
        FAIL                    No existing projects found. Cannot determine a healthy cluster for e2e-testing project.
    END

    # Use the cluster from the first existing project (it must be healthy if projects exist on it)
    ${reference_project}=                           Set Variable            ${existing_projects[0]}
    ${cluster_id}=          Set Variable            ${reference_project['cluster_id']}

    Log                     Creating e2e-testing project using cluster from existing project: ${reference_project['name']} (Cluster ID: ${cluster_id})

    # Define minimal quota for e2e testing
    ${quota_data}=          Create Dictionary
    ...                     cpu_milli_cores=1000
    ...                     memory_bytes=1073741824
    ...                     ephemeral_storage_bytes=1073741824
    ...                     gpu_count=0

    # Create project data
    ${project_data}=        Create Dictionary
    ...                     name=e2e-testing
    ...                     description=Automated e2e testing project
    ...                     cluster_id=${cluster_id}
    ...                     quota=${quota_data}

    # Create the project
    ${create_response}=     Create project          ${project_data}         expected_status=201
    ${created_project}=     Set Variable            ${create_response.json()}

    Log                     Successfully created e2e-testing project with ID: ${created_project['id']}

    # Get current user and add them to the project to resolve 403 Forbidden errors
    ${current_user}=        Get current user
    ${user_ids}=            Create List             ${current_user['id']}

    Log                     Adding current user ${current_user['email']} to project ${created_project['id']}
    ${add_user_response}=                           Add users to project    ${created_project['id']}                        ${user_ids}             expected_status=200
    Log                     Successfully added user to e2e-testing project

    RETURN                  ${created_project}

Ensure user is member of project
    [Documentation]    Ensures the current user is a member of the specified project.
    ...    Checks if user is already a member first, only adds if not already a member.
    [Arguments]             ${project_id}

    # Get current user
    ${current_user}=        Get current user

    # Check if user is already a member by getting project details
    ${project_response}=    Get project             ${project_id}           expected_status=200
    ${project_data}=        Set Variable            ${project_response.json()}

    # Check if the project data includes users
    ${users_in_project}=    Set Variable            ${project_data.get('users', [])}

    # Check if current user is already a member
    ${is_member}=           Set Variable            ${False}
    FOR    ${user_in_project}    IN    @{users_in_project}
        IF    '${user_in_project['id']}' == '${current_user['id']}'
            ${is_member}=           Set Variable            ${True}
            BREAK
        END
    END

    IF    ${is_member}
        Log                     Current user ${current_user['email']} is already a member of project ${project_id}
    ELSE
        Log                     Current user ${current_user['email']} is not a member of project ${project_id}, adding them
        ${user_ids}=            Create List             ${current_user['id']}
        ${add_response}=        Add users to project    ${project_id}           ${user_ids}             expected_status=200
        Log                     Successfully added user to project ${project_id}
    END
