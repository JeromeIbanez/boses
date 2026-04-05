_Last updated: 2026-04-05_

# Tech Stack

## Frontend

| Technology | Version | Purpose |
|---|---|---|
| Next.js | 16.2.1 | React framework (App Router) |
| React | 19.2.4 | UI library |
| React DOM | 19.2.4 | DOM renderer |
| TypeScript | ^5 | Language |
| Tailwind CSS | ^4 | Utility-first CSS |
| @tailwindcss/postcss | ^4 | Tailwind v4 PostCSS plugin |
| TanStack React Query | ^5.95.2 | Server state management |
| Lucide React | ^1.7.0 | Icon library |
| clsx | ^2.1.1 | Conditional className utility |
| tailwind-merge | ^3.5.0 | Merge Tailwind class conflicts |
| @sentry/nextjs | ^10.47.0 | Error tracking + tracing |
| eslint | ^9 | Linting |
| eslint-config-next | 16.2.1 | Next.js ESLint config |

## Backend

| Technology | Version | Purpose |
|---|---|---|
| FastAPI | 0.115.0 | REST API framework |
| Python | 3.12 | Language |
| Uvicorn | 0.30.6 (standard) | ASGI server |
| SQLAlchemy | 2.0.35 | ORM (mapped_column style) |
| Alembic | 1.13.3 | Database migrations |
| psycopg (binary) | 3.3.3 | PostgreSQL driver (psycopg3) |
| Pydantic | 2.9.2 | Data validation |
| pydantic-settings | 2.5.2 | Settings from env vars |
| OpenAI | 1.57.0 | AI completions (gpt-4o) + image generation (dall-e-3) |
| httpx | 0.27.2 | Async HTTP client (Reddit API, Supabase uploads) |
| python-multipart | 0.0.12 | File upload support |
| pdfminer.six | 20231228 | PDF text extraction |
| Pillow | 10.4.0 | Image handling |
| python-docx | 1.1.2 | Word document parsing |
| python-dotenv | 1.0.1 | .env file loading |
| python-jose (cryptography) | 3.3.0 | JWT creation + validation |
| passlib (bcrypt) | 1.7.4 | Password hashing |
| bcrypt | 3.2.2 | bcrypt backend |
| slowapi | 0.1.9 | Rate limiting middleware |
| sentry-sdk[fastapi] | 2.19.2 | Error tracking + tracing |

## Infrastructure

| Technology | Version | Purpose |
|---|---|---|
| PostgreSQL | 16 | Primary database (UUID PKs, JSONB, ARRAY) |
| Docker | — | Container runtime |
| Render.com | — | Cloud deployment platform |
| Supabase Storage | — | Persistent avatar image hosting |
| GitHub Actions | — | CI/CD |

## AI Models

| Model | Provider | Used For | Temperature |
|---|---|---|---|
| gpt-4o | OpenAI | Persona generation (pass 1) | 1.2 |
| gpt-4o | OpenAI | Persona generation (pass 2) | 1.0 |
| gpt-4o | OpenAI | Individual simulation results (concept test) | 0.9 |
| gpt-4o | OpenAI | Aggregate simulation reports | 0.7 |
| gpt-4o | OpenAI | IDI persona interviews | varies |
| gpt-4o | OpenAI | IDI transcript analysis | varies |
| gpt-4o | OpenAI | Focus group moderator + aggregate report | 0.7 |
| gpt-4o | OpenAI | Focus group persona responses | 0.9 |
| gpt-4o | OpenAI | Survey persona fill-out | 0.85 |
| gpt-4o | OpenAI | Survey aggregate + open-ended themes | 0.5–0.7 |
| gpt-4o | OpenAI | Conjoint choice tasks | 0.85 |
| gpt-4o | OpenAI | Conjoint narrative summary | 0.7 |
| gpt-4o | OpenAI | Ethnography signal extraction | 0.3 |
| gpt-4o | OpenAI | Prompt → demographic parsing | 0.2 |
| gpt-4o | OpenAI | Script/survey question extraction | 0.0 |
| dall-e-3 | OpenAI | Persona avatar portrait generation | — |

## External APIs

| API | Auth | Purpose |
|---|---|---|
| OpenAI Chat Completions | API key | All AI generation |
| OpenAI Images | API key | Persona avatar generation (DALL-E 3) |
| Reddit public JSON API | None | Social listening signals for persona grounding and ethnography crawl |
| Supabase Storage REST API | Service role key | Persistent avatar image hosting |
| Sentry | DSN | Error tracking and performance monitoring |
