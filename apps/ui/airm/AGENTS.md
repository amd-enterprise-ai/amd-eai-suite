<!--
Copyright © Advanced Micro Devices, Inc., or its affiliates.

SPDX-License-Identifier: MIT
-->

# AI Development Rules for UI

This document outlines the coding standards, architectural patterns, and development guidelines for the UI service. These rules ensure consistency, maintainability, and quality across the codebase.

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [Project Structure](#project-structure)
3. [Coding Standards](#coding-standards)
4. [Development Workflow](#development-workflow)
5. [Environment Setup](#environment-setup)
6. [Development Commands](#development-commands)

## Technology Stack

- **Frontend Framework**: Next.js with React 19
- **Language**: TypeScript
- **Styling**: TailwindCSS with HeroUI components
- **State Management**: React Context and TanStack Query (React Query)
- **Forms**: React Hook Form with Zod validation
- **Internationalization**: next-i18next
- **Testing**: Vitest with React Testing Library
- **Authentication**: NextAuth.js with Keycloak

## Project Structure

The project follows a feature-based organization pattern:

```text
/app                    # Next.js app directory with API routes
/components             # React components
  /features            # Domain-specific components organized by feature
  /shared              # Reusable components across features
  /layouts             # Page layout components
/contexts              # React context providers for global state
/hooks                 # Custom React hooks
/pages                 # Next.js page components
/public                # Static assets and localization files
  /locales             # Internationalization files
/services              # Service layer for API communication
  /app                 # Client-side services
  /server              # Server-side services
/styles                # Global styles
/types                 # TypeScript type definitions
/utils                 # Utility functions
```

### Key Architectural Patterns

1. **Component Organization**

   - Feature-based organization for domain-specific components
   - Shared components for reusable UI elements
   - Layout components for consistent page structure

2. **API Architecture**

   - Next.js API routes as proxies to backend services
   - Service layer abstraction for API communication
   - Error handling with custom error types

3. **State Management**

   - React Context for global application state
   - TanStack Query for server state management
   - React local state for component-specific state

4. **Authentication**
   - NextAuth.js for authentication with Keycloak
   - Protected routes via middleware
   - JWT token management

## Coding Standards

### General Code Style & Formatting

- **Language**: Use TypeScript for all files
- **Documentation**: Use English for all code and documentation
- **Type Safety**: Always declare the type of each variable and function (parameters and return value)
- **Avoid `any`**: Create necessary types instead of using `any`
- **Union types over enums for new code**: Prefer union types over TypeScript `enum` for new constants. Union types are erased at compile time with zero bundle cost. When you also need runtime access (iteration, lookups), pair the union with a plain `as const` object — the object itself is still runtime code, but it avoids the reverse-mapping overhead and IIFE side effects that enums introduce. Existing `enum` usage does not need to be migrated.
  ```typescript
  // Union type — sufficient when you only need compile-time type checking
  type SortDirection = 'asc' | 'desc';

  // Const object + derived union — when you also need runtime access (iteration, lookups)
  const WorkloadStatus = {
    PENDING: 'Pending',
    RUNNING: 'Running',
    COMPLETE: 'Complete',
    FAILED: 'Failed',
  } as const;

  type WorkloadStatus = (typeof WorkloadStatus)[keyof typeof WorkloadStatus];

  // Iteration — e.g., building filter dropdowns
  const statusOptions: Array<{ key: WorkloadStatus; label: WorkloadStatus }> =
    Object.values(WorkloadStatus).map((s: WorkloadStatus): { key: WorkloadStatus; label: WorkloadStatus } => ({ key: s, label: s }));

  // Lookup
  const label: WorkloadStatus = WorkloadStatus.PENDING; // 'Pending'
  ```
- **Documentation**: Use JSDoc to document public classes and methods
- **Formatting**: Don't leave blank lines within a function
- **Exports**: Prefer named exports for components

### Naming Conventions

- **Classes & Components**: Use PascalCase for classes and React components
- **Files**: Use PascalCase for React component file names (e.g., `UserCard.tsx`, not `user-card.tsx`)
- **Variables & Functions**: Use camelCase for variables, functions, and methods
- **Directories**: Use kebab-case for file and directory names
- **Environment Variables**: Use UPPERCASE for environment variables
- **Constants**: Avoid magic numbers and define constants

### Functions & Logic

- **Function Size**: Keep functions short and single-purpose (<20 lines)
- **Code Structure**: Avoid deeply nested blocks by:
  - Using early returns
  - Extracting logic into utility functions
- **Functional Programming**: Use higher-order functions (map, filter, reduce) to simplify logic
- **Function Types**: Use arrow functions for simple cases (<3 instructions), named functions otherwise
- **Parameters**: Use default parameter values instead of null/undefined checks
- **Parameter Pattern**: Use RO-RO (Receive Object, Return Object) for passing and returning multiple parameters

### Component Structure

- **Component Type**: Use functional components with hooks
- **Single Responsibility**: Keep components focused on a single responsibility
- **Custom Hooks**: Extract reusable logic into custom hooks
- **Props**: Use proper prop types with destructuring

### Styling & UI

- **Component Library**: Use HeroUI for components
- **CSS Framework**: Use Tailwind CSS for styling
- **Responsive Design**: Follow responsive design principles

### Data Fetching & Forms

- **Data Fetching**: Use TanStack Query (react-query) for frontend data fetching
- **Form Handling**: Use React Hook Form for form handling
- **Validation**: Use Zod for validation
- **API Updates**: When updating resources, only send fields that are actually mutable
- **Type Definitions**: Keep type definitions minimal and focused on their purpose

### Internationalization

- **Translation Keys**: Never add hardcoded fallbacks in code for translations
- **Consistency**: Use translation keys consistently throughout the application
- **Organization**: Keep translation files organized by feature area
- **Key Names**: Always provide meaningful keys that describe the content

### Testing Standards

- **Test Coverage**: Write tests for components and utilities
- **Testing Library**: Use React Testing Library for component testing
- **Mocking**: Mock external dependencies
- **Test Command**: Run tests with `pnpm test`
- **IMPORTANT - Specific File Testing**: When you have a React component `*.tsx` file or a test file `*.test.tsx` in the context and the user asks for running tests, ALWAYS run tests for the specific corresponding test file instead of running all the tests.
  - For component files like `components/shared/ManagedForm/FormSelect.tsx`, run: `pnpm test __tests__/components/shared/ManagedForm/FormSelect.test.tsx`
  - For files in `hooks/` like `hooks/useAccessControl.ts`, run: `pnpm test __tests__/hooks/useAccessControl.test.tsx`
  - For files in `pages/` like `pages/index.tsx`, run: `pnpm test __tests__/pages/index.test.tsx`

## CamelCase API Convention

All API responses and requests use camelCase field names. The backend enforces this via middleware (HTTP 422 for snake_case).

### Rules

- **Request bodies**: Use camelCase keys — `{ userId: "..." }` not `{ user_id: "..." }`.
- **Query parameters**: Use camelCase — `?pageSize=10&sortBy=name` not `?page_size=10&sort_by=name`.
- **TypeScript types**: All API-facing type properties use camelCase — `cpuMilliCores`, `gpuCount`, `memoryBytes`.
- **Response handling**: `response.json()` returns camelCase directly, no conversion needed.

### Exceptions (fields that stay snake_case)

- **OpenAI chat types** (`chat.ts`): `stream_options`, `prompt_tokens`, `completion_tokens` — OpenAI spec. The `/chat` endpoint is excluded from camelCase enforcement.
- **OAuth2/OIDC fields**: `client_id`, `grant_type`, `refresh_token` — external protocol spec.
- **Metric name values**: Strings like `'total_tokens'` passed as values to metric APIs.

## Development Workflow

### Code Quality

- Use TypeScript strict mode for type safety
- Follow the established linting and formatting rules
- Write meaningful commit messages
- Create feature branches for new development
- Use pull requests for code review

### Best Practices

- Test your changes before committing
- Keep components small and focused
- Document complex logic with comments
- Follow the established naming conventions
- Ensure responsive design compatibility

## Environment Setup

### Required Environment Variables

```bash
NEXTAUTH_SECRET=<secret-for-nextauth>
NEXTAUTH_URL=<url-for-nextauth-eg-http://localhost:8000>
KEYCLOAK_ID=<keycloak-client-id>
KEYCLOAK_SECRET=<keycloak-client-secret>
KEYCLOAK_ISSUER=<keycloak-issuer-url>
AIRM_API_SERVICE_URL=<url-for-airm-api-service>
```

### Initial Setup

```bash
# Install dependencies
pnpm i
```

## Development Commands

### Development

```bash
# Start development server on port 8000
pnpm dev

# Check TypeScript errors
pnpm typecheck

# Format code
pnpm format:fix

# Check formatting
pnpm format:check

# Lint code and fix issues
pnpm lint
```

### Testing

```bash
# Run all tests
pnpm test

# Run specific test file
pnpm test path/to/test/file.test.tsx

# Run all tests in watch mode
pnpm test:watch

# Run tests with coverage
pnpm coverage
```
