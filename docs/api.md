_Last updated: 2026-04-05_

# API Reference

Base URL: `https://api.temujintechnologies.com/api/v1`
Staging URL: `https://api-staging.temujintechnologies.com/api/v1`

All authenticated endpoints require a valid `access_token` httpOnly cookie. Tokens are issued by the auth endpoints and refreshed automatically by the frontend.

## Auth (`/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | No | Register new user + company (10/hour rate limit) |
| POST | `/auth/login` | No | Authenticate, set token cookies (20/min rate limit) |
| POST | `/auth/logout` | No | Revoke refresh token, clear cookies |
| GET | `/auth/me` | Yes | Get current user |
| POST | `/auth/refresh` | No | Rotate access + refresh tokens |
| POST | `/auth/forgot-password` | No | Send password reset email (5/hour rate limit) |
| POST | `/auth/reset-password` | No | Reset password with token |

## Projects (`/projects`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/projects` | Yes | List all projects for the company |
| POST | `/projects` | Yes | Create a project |
| GET | `/projects/{project_id}` | Yes | Get project details |
| PATCH | `/projects/{project_id}` | Yes | Update project name/description |
| DELETE | `/projects/{project_id}` | Yes | Delete project (cascades) |

## Persona Groups (`/projects/{project_id}/persona-groups`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/persona-groups/parse-prompt` | Yes | Parse natural language → demographic fields (OpenAI) |
| GET | `/persona-groups` | Yes | List persona groups for project |
| POST | `/persona-groups` | Yes | Create persona group |
| GET | `/persona-groups/{group_id}` | Yes | Get persona group |
| PATCH | `/persona-groups/{group_id}` | Yes | Update persona group |
| DELETE | `/persona-groups/{group_id}` | Yes | Delete persona group (cascades) |
| POST | `/persona-groups/{group_id}/generate` | Yes | Generate personas (background task, returns 202); also lazily queues a cultural context refresh |

## Personas (`/projects/{project_id}/persona-groups/{group_id}/personas`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/personas` | Yes | List personas in group |
| GET | `/personas/{persona_id}` | Yes | Get single persona |
| DELETE | `/personas` | Yes | Delete all personas in group |
| DELETE | `/personas/{persona_id}` | Yes | Delete single persona |

## Briefings (`/projects/{project_id}/briefings`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/briefings` | Yes | List briefings for project |
| POST | `/briefings` | Yes | Upload briefing file (PDF, image, text) |
| GET | `/briefings/{briefing_id}` | Yes | Get briefing details |
| DELETE | `/briefings/{briefing_id}` | Yes | Delete briefing + file |

## Simulations (`/projects/{project_id}/simulations`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/simulations` | Yes | List simulations for project |
| POST | `/simulations` | Yes | Create + start simulation (background task, returns 201) |
| GET | `/simulations/{simulation_id}` | Yes | Get simulation status (includes 20-min timeout check) |
| POST | `/simulations/{simulation_id}/abort` | Yes | Abort a running simulation |
| DELETE | `/simulations/{simulation_id}` | Yes | Delete simulation |
| GET | `/simulations/{simulation_id}/results` | Yes | Get simulation results |
| POST | `/simulations/{simulation_id}/script` | Yes | Upload IDI script (.txt or .docx); LLM-extracts questions; auto-starts idi_ai |
| GET | `/simulations/{simulation_id}/messages` | Yes | Get IDI chat messages |
| POST | `/simulations/{simulation_id}/messages` | Yes | Send message in manual IDI session |
| POST | `/simulations/{simulation_id}/end` | Yes | End manual IDI session and trigger report generation |
| POST | `/simulations/{simulation_id}/survey` | Yes | Upload survey file (.txt or .docx); LLM-parses into survey_schema; does NOT start run |
| POST | `/simulations/{simulation_id}/run` | Yes | Confirm parsed survey questions and start survey simulation |
| POST | `/simulations/{simulation_id}/conjoint-design` | Yes | Submit conjoint attribute/level design and start simulation |
| GET | `/simulations/convergence` | Yes | Cross-simulation convergence scores (query params: persona_group_id, briefing_id?) |
| POST | `/simulations/{simulation_id}/reliability-check` | Yes | Kick off N repeat runs to compute a confidence score |
| GET | `/simulations/{simulation_id}/reliability-check` | Yes | Get latest reliability study for a simulation |

### Simulation Types

| Type | Description |
|---|---|
| `concept_test` | Runs all personas against a briefing; generates individual + aggregate results |
| `idi_ai` | Automated multi-turn interview of each persona using a script |
| `idi_manual` | User chats interactively with a single AI persona |
| `focus_group` | Multi-turn group discussion across 2 rounds with a moderator LLM |
| `survey` | Each persona fills out a structured survey (likert, multiple_choice, open_ended) |
| `conjoint` | Choice-based conjoint analysis — personas choose between product attribute profiles |

### Simulation Status Values

`pending` → `running` → `generating_report` → `complete` | `failed` | `aborted`

`active` — used by `idi_manual` sessions while the interview is in progress.

## Library (`/library`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/library/personas` | Yes | Search library personas (filters: location, gender, income_level, age_min, age_max, occupation, limit, offset) |
| GET | `/library/personas/{id}` | Yes | Get library persona details |
| GET | `/library/personas/{id}/projects` | Yes | Find projects using this persona |
| POST | `/library/personas/{id}/retire` | Yes | Mark persona as retired |
| DELETE | `/library/personas/{id}` | Yes | Hard-delete a library persona |
| DELETE | `/library/personas` | Yes | Hard-delete all library personas |

## Internal (`/internal`)

These endpoints are disabled in production (`is_production=True`). Available in development and staging only.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/internal/ethnography/refresh/{market_code}` | No | Manually trigger a cultural context refresh for a market (ID / PH / VN). Returns 202 immediately; runs as a background task. |

## Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Service health check → `{"status": "ok"}` |
