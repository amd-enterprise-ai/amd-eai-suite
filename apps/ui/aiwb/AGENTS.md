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
   - Route files should be thin re-exports from handlers in `@/lib/server/`:

     ```typescript
     // Standard JSON proxy (most routes)
     export { GET, POST } from "@/lib/server/proxy-handler";

     // AIM chat (direct-to-AIM bypass — UI-only route under app/api/ui/)
     export { POST } from "@/lib/server/aim-chat-handler";

     // Streaming logs proxy
     export { GET } from "@/lib/server/streaming-logs-handler";
     ```

   - **Backend-mirror routes** live under `app/api/...` and mirror backend API paths (`openapi.json`) — e.g., `app/api/namespaces/[namespace]/...`, `app/api/projects/[project]/...`. These are 1:1 proxies and use `proxy-handler` or the streaming handlers.
   - **UI-only routes** live under `app/api/ui/...` and do not mirror a single backend endpoint. Use this namespace whenever the route's logic is server-side glue that belongs to the UI rather than to the backend API — for example, the AIM chat bypass at `app/api/ui/projects/[project]/inference/[id]/chat/` fetches the AIM via the backend, then POSTs directly to the AIM's in-cluster internal URL. Pick this namespace when the route has its own handler logic (auth caching, multiple upstream calls, browser-only concerns) rather than acting as a thin proxy.
   - Special routes (`auth/`, `health/`) are non-proxy
   - Data transformation or parsing logic belongs in `@/lib/`, not in route files
   - Only export HTTP methods the backend actually supports
   - Routes that re-export `proxy-handler` can be unit-tested with the `vi.mock('@amdenterpriseai/utils/server', ...)` pattern overriding `proxyRequest` (see `__tests__/lib/server/proxy-handler.test.ts`). Routes backed by a dedicated handler (chat, streaming logs, dataset upload/download) don't go through `proxy-handler`, so that pattern doesn't apply — test the handler directly.

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

### Performance

`useMemo` and `useCallback` are performance hints, not free abstractions — each call site costs a dependency-array store plus a shallow compare on every render, in addition to the cognitive overhead of reading them. Reach for them only when **both** are true: (1) the computation is genuinely expensive (sorting large lists, recursive walks, non-trivial transforms) **or** the result is a non-primitive passed to a `React.memo`'d child or another hook's dep array where referential equality matters; **and** (2) render-frequency × computation-cost is meaningful — you can measure or reason about a real regression without the memo. Skip them for primitives, cheap derivations (`xs.length > 0`, `obj.prop`, simple ternaries), values whose deps change on every render anyway, and callbacks passed to vanilla DOM elements. The codebase has accumulated many cargo-cult memoization call sites; do not add to the pile. See https://react.dev/reference/react/useMemo for the official guidance.

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
- **`staleTime: Infinity` for session-immutable data**: When a `useQuery` returns data that only changes on an out-of-band event (engine reinstall, cluster reconfig, chart bump) — not on user action and not on a polling cycle — set `staleTime: Infinity` on the query config. Without it, React Query treats the cached data as stale and re-fetches it on every window-focus, reconnect, and component remount for data that is structurally stable for the entire session. See `apps/ui/aiwb/hooks/useProfileSpecsForServices.ts` (`PROFILE_CACHE_MS = Infinity` for the AIMProfile / AIMClusterProfile catalogs) for the pattern.
- **Don't shadow a canonical BE field with a FE-side computed wrapper**: Read the BE field directly at call sites (e.g., `s.spec.model?.name`). If the field needs a default or a cross-field fallback, fix it BE-side via a Pydantic `model_validator(mode="after")` — not by introducing a FE-side computed value (`useMemo(() => x.foo ?? x.bar, [x])`, a derived selector, a `getModelResourceName(s)` helper) at every consumer. Computed wrappers create a parallel naming convention that has to be kept in sync, hide the source-of-truth question, and accumulate as the canonical field evolves. *(Paired BE rule in `apps/api/aiwb/AGENTS.md` § Data Architecture #6: the BE side is responsible for backfilling the canonical field via `model_validator(mode="after")`; this FE rule is the consumer-side complement.)*

### Internationalization

- **Compile-Time Enforcement**: `types/react-i18next.d.ts` augments i18next's `CustomTypeOptions` with nested resource types, so `t('invalid.key')` is a compile error. Run `pnpm typecheck` to verify.
- **Key Documentation**: `types/react-i18next.d.ts` also exports flat dot-separated string union types per namespace (e.g. `chatKeys`) for typed wrapper functions.
- **Translation Keys**: Never add hardcoded fallbacks in code for translations
- **Consistency**: Use translation keys consistently throughout the application
- **Organization**: Keep translation files organized by feature area
- **Key Names**: Always provide meaningful keys that describe the content
- **Type Generation**: Run `pnpm i18n:types` after modifying translation JSON files to regenerate types
- **Static Lookup Tables**: When mapping a runtime value (enum member, error code, status string) to a translation key, define the map once and use `translationKeyGenerator(map, defaultKey?)` from `lib/app/i18n.ts` to derive a type-safe getter. The getter handles unknown values by returning either the default-key's translation key (when a default is provided) or `undefined`. Name getters with the `TranslationKey` suffix to disambiguate from React/object keys — see `getMetricTranslationKey` in `lib/app/aims.ts` and `getErrorTitleTranslationKey` / `getErrorDescriptionTranslationKey` in `lib/app/errorMessages.ts` for canonical examples.
- **Shared Components**: Components under `apps/ui/shared/` are consumed by multiple apps and cannot know which namespace the caller will use. They use `as any` casts on `useTranslation(ns)` and `t(key)` calls and a structurally-typed `t` prop, since the augmented `TFunction` is bound to a single namespace at compile time. This is tracked in EAI-5617; do not propagate this pattern into app-level code.

### Testing Standards

- **Test Coverage**: Write tests for components and utilities
- **Testing Library**: Use React Testing Library for component testing
- **Mocking**: Mock external dependencies
- **Test Command**: Run tests with `pnpm test`
- **IMPORTANT - Specific File Testing**: When you have a React component `*.tsx` file or a test file `*.test.tsx` in the context and the user asks for running tests, ALWAYS run tests for the specific corresponding test file instead of running all the tests.
  - For component files like `components/shared/ManagedForm/FormSelect.tsx`, run: `pnpm test __tests__/components/shared/ManagedForm/FormSelect.test.tsx`
  - For files in `hooks/` like `hooks/useAccessControl.ts`, run: `pnpm test __tests__/hooks/useAccessControl.test.tsx`
  - For files in `pages/` like `pages/index.tsx`, run: `pnpm test __tests__/pages/index.test.tsx`

### Server-Side Logging

- **Informational logs**: Remove `console.info` / `console.log` calls from server-side code unless they carry clear production debugging value. Unconditional informational logging pollutes vitest stderr.
- **Error logs**: Reserve `logger.error` / `console.error` for genuinely unexpected failures (5xx and unknown thrown values). Do not log `RouteError` instances with 4xx statuses — callers intentionally surface those as HTTP responses.
- **Testing error paths**: Mock `handleError` to isolate the error contract from logging side effects — see `__tests__/lib/server/proxy-handler.test.ts` for a model.

### Paginated List Loaders

When a service-layer function needs **every** item from a paginated backend endpoint (typically because a UI consumer cannot yet drive server-side pagination), **always use `fetchAllPages` from `@/lib/app/pagination`** instead of hand-rolling a `Promise.all` walker.

Why:

- `fetchAllPages` bounds in-flight requests so the browser never fires N concurrent connections at the backend on large datasets (the silent failure mode is request throttling/timeouts, not a visible bug).
- It staggers request kickoffs with a small delay so a single client cannot burst the backend even within a batch.
- Centralizing the walker means tuning concurrency / delay defaults is a one-line change across every consumer.

```ts
// GOOD — uses the shared walker
import { fetchAllPages } from '@/lib/app/pagination';

export const getAllDatasets = (projectId: string, filters: ListDatasetsOptions = {}): Promise<Dataset[]> =>
  fetchAllPages<Dataset>((page, pageSize) =>
    listDatasets(projectId, { ...filters, page, pageSize }),
  );

// BAD — raw Promise.all over `totalPages - 1`. Unbounded burst on large
// projects and no inter-request stagger.
const firstPage = await listDatasets(projectId, { ...filters, page: 1, pageSize: 100 });
const totalPages = Math.ceil(firstPage.pagination.total / 100);
const remaining = await Promise.all(
  Array.from({ length: totalPages - 1 }, (_, i) =>
    listDatasets(projectId, { ...filters, page: i + 2, pageSize: 100 }),
  ),
);
```

The expected per-endpoint pattern is **two functions**: a single-page `listX(page, pageSize, ...filters)` that returns the raw `PaginatedList<T>`, plus a walk-all `getAllX(...)` (or `listAllX(...)`) that thin-wraps `fetchAllPages`. Server-side-paginated tables consume the former; load-all consumers (dropdowns, joins, exports) consume the latter.

**This is a stop-gap pattern.** Each load-all consumer should track a follow-up to migrate to a server-side paginated table; once migrated, the `getAllX` wrapper can be retired.

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

## Value and Identifier Hygiene

Two habits that keep data correct as it crosses the FE/BE boundary:

1. **Use the right identifier across machine boundaries.** When an entity carries
   both a human-facing display name and the id an external system resolves against,
   send the resolved id wherever a value crosses a machine boundary (API request
   fields, downstream calls, generated code snippets) and reserve the display name
   for what the user reads. Passing a display name where an id is expected
   typechecks (both are `string`) but fails at runtime.

2. **Don't add redundant nullish coercions or over-wide types.** When a value is
   already nullable, or its consumer already handles the nullish/falsy case,
   coercing it (`?? null`, `?? ''`, `?? undefined`) is dead weight — let the
   nullable value flow straight to the place that resolves it. Likewise, don't
   widen a parameter type to accept a nullish value it never receives.

```ts
// BAD
buildRequest({ resourceId: item.label });  // label is for humans; remote can't resolve it
const id = spec.id ?? null;                // spec.id is already `string | undefined`
const safeId = id ?? '';                   // the consumer below already handles falsy
useId(safeId);
function useId(id?: string | null) {       // over-wide — accepts a null it never needs
  const resolved = id || 'default';
}

// GOOD
buildRequest({ resourceId: item.id });     // the id the downstream system resolves against
useId(spec.id);                            // pass the optional value straight through
function useId(id?: string) {
  const resolved = id || 'default';
}
```

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

### Internationalization

```bash
# Generate TypeScript types from translation JSON files
pnpm i18n:types
```
