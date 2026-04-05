_Last updated: 2026-04-05_

# Frontend

Built with Next.js 16.2.1 using the App Router. TypeScript throughout. Sentry error tracking via `@sentry/nextjs`.

## Route Tree

```mermaid
graph TD
    ROOT["/\nRedirects based on auth"]
    AUTH_GROUP["(auth) route group\nNo URL segment"]
    LOGIN["/login"]
    SIGNUP["/signup"]
    FORGOT["/forgot-password"]
    RESET["/reset-password"]
    DASH["/dashboard"]
    PROJ["/projects"]
    PROJ_ID["/projects/:projectId"]
    PERSONA_GRP["/projects/:projectId/personas/:groupId"]
    PERSONA_DETAIL["/projects/:projectId/personas/:groupId/:personaId"]
    SIM_ID["/projects/:projectId/simulations/:simulationId"]
    SIM_CHAT["/projects/:projectId/simulations/:simulationId/chat"]
    SIM_TRANSCRIPT["/projects/:projectId/simulations/:simulationId/transcript"]
    SIM_SURVEY_EXPORT["/projects/:projectId/simulations/:simulationId/survey-export"]
    PERSONAS_LIB["/personas"]
    PERSONA_LIB_DETAIL["/personas/:id"]

    ROOT -->|"authenticated"| DASH
    ROOT -->|"unauthenticated"| LOGIN

    AUTH_GROUP --> LOGIN
    AUTH_GROUP --> SIGNUP
    AUTH_GROUP --> FORGOT
    AUTH_GROUP --> RESET

    DASH --> PROJ
    PROJ --> PROJ_ID
    PROJ_ID -->|"Personas tab"| PERSONA_GRP
    PERSONA_GRP --> PERSONA_DETAIL
    PROJ_ID -->|"Simulations tab"| SIM_ID
    SIM_ID --> SIM_CHAT
    SIM_ID --> SIM_TRANSCRIPT
    SIM_ID --> SIM_SURVEY_EXPORT
    PERSONAS_LIB --> PERSONA_LIB_DETAIL
```

## Auth Redirect Logic (middleware.ts)

| Condition | Action |
|---|---|
| No `access_token` cookie + protected route | Redirect to `/login` |
| Has `access_token` cookie + auth route (`/login`, `/signup`, etc.) | Redirect to `/dashboard` |
| All other cases | Allow through |

Public paths (no auth required): `/login`, `/signup`, `/forgot-password`, `/reset-password`

## Route Reference

| Route | Component | Notes |
|---|---|---|
| `/` | `app/page.tsx` | Redirects via middleware |
| `/login` | `app/(auth)/login/page.tsx` | |
| `/signup` | `app/(auth)/signup/page.tsx` | |
| `/forgot-password` | `app/(auth)/forgot-password/page.tsx` | |
| `/reset-password` | `app/(auth)/reset-password/page.tsx` | |
| `/dashboard` | `app/dashboard/page.tsx` | Project cards overview |
| `/projects` | `app/projects/page.tsx` | Project list |
| `/projects/:projectId` | `app/projects/[projectId]/page.tsx` | Tabbed: Briefings, Personas, Simulations |
| `/projects/:projectId/personas/:groupId` | `app/projects/[projectId]/personas/[groupId]/page.tsx` | Persona group detail + list |
| `/projects/:projectId/personas/:groupId/:personaId` | `app/projects/[projectId]/personas/[groupId]/[personaId]/page.tsx` | Individual persona detail |
| `/projects/:projectId/simulations/:simulationId` | `app/projects/[projectId]/simulations/[simulationId]/page.tsx` | Results / status |
| `/projects/:projectId/simulations/:simulationId/chat` | `.../chat/page.tsx` | Manual IDI chat interface |
| `/projects/:projectId/simulations/:simulationId/transcript` | `.../transcript/page.tsx` | IDI transcript view |
| `/projects/:projectId/simulations/:simulationId/survey-export` | `.../survey-export/page.tsx` | Survey results export view |
| `/personas` | `app/personas/page.tsx` | Persona library browser |
| `/personas/:id` | `app/personas/[id]/page.tsx` | Library persona detail |

## API Client

`frontend/lib/api.ts` wraps `fetch()` with:
- Base URL: `process.env.NEXT_PUBLIC_API_URL`
  - Dev: `http://localhost:8000/api/v1`
  - Production: `https://api.temujintechnologies.com/api/v1`
  - Staging: `https://api-staging.temujintechnologies.com/api/v1`
- `credentials: "include"` on all requests (sends cookies)
- `Content-Type: application/json` default

## State Management

TanStack Query (`@tanstack/react-query` v5) handles all server state:
- Queries for list/detail endpoints
- Mutations for create/update/delete
- Polling for simulation status (until `status === "complete"` or `"failed"`)

Auth state is managed via `AuthContext` (`frontend/contexts/AuthContext.tsx`), which stores the current user and exposes login/logout functions.

## Observability

Sentry is configured via three instrumentation files:
- `frontend/instrumentation.ts` — server-side
- `frontend/sentry.client.config.ts` — browser
- `frontend/sentry.edge.config.ts` — edge runtime
- `frontend/sentry.server.config.ts` — Node.js server
