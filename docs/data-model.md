_Last updated: 2026-04-05_

# Data Model

All tables use UUID primary keys. Timestamps are timezone-aware. The database is PostgreSQL 16 with JSONB and ARRAY column support.

## ER Diagram

```mermaid
erDiagram
    companies {
        uuid id PK
        string name
        string slug UK
        datetime created_at
        datetime updated_at
    }
    users {
        uuid id PK
        uuid company_id FK
        string email UK
        string hashed_password
        string full_name
        string role
        bool is_active
        string password_reset_token
        datetime password_reset_token_expiry
        datetime created_at
        datetime updated_at
    }
    refresh_tokens {
        uuid id PK
        uuid user_id FK
        string token_hash
        datetime expires_at
        datetime revoked_at
        datetime created_at
    }
    projects {
        uuid id PK
        uuid company_id FK
        string name
        text description
        datetime created_at
        datetime updated_at
    }
    persona_groups {
        uuid id PK
        uuid project_id FK
        string name
        text description
        int age_min
        int age_max
        string gender
        string location
        string occupation
        string income_level
        text psychographic_notes
        int persona_count
        string generation_status
        jsonb generation_progress
        datetime created_at
        datetime updated_at
    }
    personas {
        uuid id PK
        uuid persona_group_id FK
        uuid library_persona_id FK
        string full_name
        int age
        string gender
        string location
        string occupation
        string income_level
        text educational_background
        text family_situation
        array personality_traits
        text values_and_motivations
        text pain_points
        text media_consumption
        text purchase_behavior
        string archetype_label
        string psychographic_segment
        text brand_attitudes
        text buying_triggers
        text aspirational_identity
        text digital_behavior
        string persona_code UK
        text avatar_url
        text day_in_the_life
        string data_source
        array data_source_references
        jsonb raw_profile_json
        datetime created_at
    }
    library_personas {
        uuid id PK
        string full_name
        int age
        string gender
        string location
        string occupation
        string income_level
        text educational_background
        text family_situation
        text background
        array personality_traits
        text goals
        text pain_points
        string tech_savviness
        text media_consumption
        text spending_habits
        string archetype_label
        string psychographic_segment
        text brand_attitudes
        text buying_triggers
        text aspirational_identity
        text digital_behavior
        text day_in_the_life
        text avatar_url
        string data_source
        array data_source_references
        int simulation_count
        bool is_retired
        datetime created_at
        datetime updated_at
    }
    persona_library_links {
        uuid id PK
        uuid persona_id FK
        uuid library_persona_id FK
        float match_score
        datetime linked_at
    }
    briefings {
        uuid id PK
        uuid project_id FK
        string title
        text description
        string file_name
        string file_path
        string file_type
        text extracted_text
        datetime created_at
    }
    simulations {
        uuid id PK
        uuid project_id FK
        uuid persona_group_id FK
        uuid briefing_id FK
        text prompt_question
        string simulation_type
        text idi_script_text
        uuid idi_persona_id FK
        jsonb survey_schema
        string status
        text error_message
        jsonb progress
        datetime created_at
        datetime completed_at
    }
    simulation_results {
        uuid id PK
        uuid simulation_id FK
        uuid persona_id FK
        string result_type
        string sentiment
        float sentiment_score
        text reaction_text
        array key_themes
        text notable_quote
        text summary_text
        jsonb sentiment_distribution
        array top_themes
        text recommendations
        text transcript
        jsonb report_sections
        datetime created_at
    }
    idi_messages {
        uuid id PK
        uuid simulation_id FK
        uuid persona_id FK
        string role
        text content
        datetime created_at
    }
    cultural_context_snapshots {
        uuid id PK
        string market_code
        string status
        int version
        jsonb signals_json
        jsonb raw_sources
        float quality_score
        datetime created_at
        datetime activated_at
    }
    reproducibility_studies {
        uuid id PK
        uuid project_id FK
        uuid source_simulation_id FK
        int n_runs
        string status
        float sentiment_agreement_rate
        float distribution_variance_score
        float theme_overlap_coefficient
        float confidence_score
        jsonb score_breakdown
        datetime created_at
        datetime completed_at
    }
    reproducibility_runs {
        uuid id PK
        uuid study_id FK
        uuid simulation_id FK
        int run_index
        datetime created_at
    }

    companies ||--o{ users : "has"
    companies ||--o{ projects : "owns"
    users ||--o{ refresh_tokens : "has"
    projects ||--o{ persona_groups : "has"
    projects ||--o{ briefings : "has"
    projects ||--o{ simulations : "has"
    projects ||--o{ reproducibility_studies : "has"
    persona_groups ||--o{ personas : "contains"
    persona_groups ||--o{ simulations : "used in"
    personas ||--o| persona_library_links : "linked via"
    library_personas ||--o{ persona_library_links : "linked via"
    briefings ||--o{ simulations : "used in"
    simulations ||--o{ simulation_results : "produces"
    simulations ||--o{ idi_messages : "has"
    simulations ||--o{ reproducibility_runs : "tracked by"
    personas ||--o{ simulation_results : "generates"
    personas ||--o{ idi_messages : "speaks in"
    reproducibility_studies ||--o{ reproducibility_runs : "contains"
```

## Table Reference

### Auth Domain

**companies**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| name | String(255) | No | |
| slug | String(100) | No | Unique |
| created_at | DateTime(tz) | No | |
| updated_at | DateTime(tz) | No | |

**users**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| company_id | UUID | No | FK → companies.id |
| email | String(255) | No | Unique, indexed |
| hashed_password | String(255) | No | bcrypt |
| full_name | String(255) | Yes | |
| role | String(50) | No | Default: "owner" |
| is_active | Boolean | No | Default: true |
| password_reset_token | String(255) | Yes | |
| password_reset_token_expiry | DateTime(tz) | Yes | |
| created_at | DateTime(tz) | No | |
| updated_at | DateTime(tz) | No | |

**refresh_tokens**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| user_id | UUID | No | FK → users.id, CASCADE |
| token_hash | String(255) | No | Indexed; stored as bcrypt hash |
| expires_at | DateTime(tz) | No | |
| revoked_at | DateTime(tz) | Yes | Null = active |
| created_at | DateTime(tz) | No | |

### Core Domain

**projects**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| company_id | UUID | Yes | FK → companies.id, indexed |
| name | String(255) | No | |
| description | Text | Yes | |
| created_at | DateTime | No | |
| updated_at | DateTime | No | |

### Persona Domain

**persona_groups**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| project_id | UUID | No | FK → projects.id |
| name | String(255) | No | |
| description | Text | Yes | |
| age_min | Integer | No | |
| age_max | Integer | No | |
| gender | String(50) | No | |
| location | String(255) | No | |
| occupation | String(255) | No | |
| income_level | String(100) | No | |
| psychographic_notes | Text | Yes | |
| persona_count | Integer | No | Default: 5 |
| generation_status | String(50) | No | pending / generating / complete / failed |
| generation_progress | JSONB | Yes | Per-persona step tracking |
| created_at | DateTime | No | |
| updated_at | DateTime | No | |

**personas**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| persona_group_id | UUID | No | FK → persona_groups.id |
| library_persona_id | UUID | Yes | FK → library_personas.id |
| full_name | String(255) | No | |
| age | Integer | No | |
| gender | String(50) | No | |
| location | String(255) | No | |
| occupation | String(255) | No | |
| income_level | String(100) | No | |
| educational_background | Text | Yes | |
| family_situation | Text | Yes | |
| personality_traits | ARRAY(String) | Yes | |
| values_and_motivations | Text | Yes | |
| pain_points | Text | Yes | |
| media_consumption | Text | Yes | |
| purchase_behavior | Text | Yes | |
| archetype_label | String(100) | Yes | e.g. "The Achiever" |
| psychographic_segment | String(100) | Yes | VALS-style segment |
| brand_attitudes | Text | Yes | |
| buying_triggers | Text | Yes | |
| aspirational_identity | Text | Yes | |
| digital_behavior | Text | Yes | |
| persona_code | String(8) | No | Unique short ID |
| avatar_url | Text | Yes | Supabase URL or /uploads path |
| day_in_the_life | Text | Yes | |
| data_source | String(50) | No | synthetic / library |
| data_source_references | ARRAY(String) | Yes | Reddit post URLs etc. |
| raw_profile_json | JSONB | Yes | Full GPT output |
| created_at | DateTime | No | |

**library_personas**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| full_name | String(255) | No | |
| age | Integer | No | |
| gender | String(50) | No | |
| location | String(255) | No | |
| occupation | String(255) | No | |
| income_level | String(100) | No | |
| educational_background | Text | Yes | |
| family_situation | Text | Yes | |
| background | Text | Yes | |
| personality_traits | ARRAY(String) | Yes | |
| goals | Text | Yes | |
| pain_points | Text | Yes | |
| tech_savviness | String(100) | Yes | |
| media_consumption | Text | Yes | |
| spending_habits | Text | Yes | |
| archetype_label | String(100) | Yes | |
| psychographic_segment | String(100) | Yes | |
| brand_attitudes | Text | Yes | |
| buying_triggers | Text | Yes | |
| aspirational_identity | Text | Yes | |
| digital_behavior | Text | Yes | |
| day_in_the_life | Text | Yes | |
| avatar_url | Text | Yes | Propagated from project personas |
| data_source | String(50) | No | Default: synthetic |
| data_source_references | ARRAY(String) | Yes | |
| simulation_count | Integer | No | Default: 0 |
| is_retired | Boolean | No | Default: false |
| created_at | DateTime(tz) | No | |
| updated_at | DateTime(tz) | No | |

**persona_library_links**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| persona_id | UUID | No | FK → personas.id, CASCADE, unique |
| library_persona_id | UUID | No | FK → library_personas.id |
| match_score | Float | Yes | 0.0–1.0; threshold 0.70; null = freshly generated |
| linked_at | DateTime(tz) | No | |

### Simulation Domain

**briefings**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| project_id | UUID | No | FK → projects.id |
| title | String(255) | No | |
| description | Text | Yes | |
| file_name | String(500) | No | |
| file_path | String(1000) | No | Absolute path under UPLOAD_DIR |
| file_type | String(50) | No | pdf / image / text |
| extracted_text | Text | Yes | Extracted by pdfminer or OCR |
| created_at | DateTime | No | |

**simulations**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| project_id | UUID | No | FK → projects.id |
| persona_group_id | UUID | No | FK → persona_groups.id, CASCADE |
| briefing_id | UUID | Yes | FK → briefings.id, SET NULL |
| prompt_question | Text | Yes | |
| simulation_type | String(50) | No | concept_test / idi_ai / idi_manual / focus_group / survey / conjoint |
| idi_script_text | Text | Yes | Parsed from uploaded .txt/.docx |
| idi_persona_id | UUID | Yes | FK → personas.id, SET NULL |
| survey_schema | JSONB | Yes | Parsed survey/conjoint design |
| status | String(50) | No | pending / running / active / generating_report / complete / failed / aborted |
| error_message | Text | Yes | |
| progress | JSONB | Yes | Per-persona completion tracking |
| created_at | DateTime | No | |
| completed_at | DateTime | Yes | |

**simulation_results**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| simulation_id | UUID | No | FK → simulations.id |
| persona_id | UUID | Yes | FK → personas.id, SET NULL; null for aggregate rows |
| result_type | String(50) | No | individual / aggregate / idi_individual / idi_aggregate / focus_group_individual / focus_group_aggregate / survey_individual / survey_aggregate / conjoint_individual / conjoint_aggregate |
| sentiment | String(50) | Yes | positive / neutral / negative |
| sentiment_score | Float | Yes | -1.0 to 1.0 |
| reaction_text | Text | Yes | Full persona reaction |
| key_themes | ARRAY(String) | Yes | |
| notable_quote | Text | Yes | |
| summary_text | Text | Yes | Aggregate summary |
| sentiment_distribution | JSONB | Yes | {positive: %, neutral: %, negative: %} |
| top_themes | ARRAY(String) | Yes | |
| recommendations | Text | Yes | |
| transcript | Text | Yes | IDI full transcript |
| report_sections | JSONB | Yes | Structured report for IDI/focus group/survey/conjoint |
| created_at | DateTime | No | |

**idi_messages**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| simulation_id | UUID | No | FK → simulations.id, CASCADE |
| persona_id | UUID | Yes | FK → personas.id, SET NULL |
| role | String(20) | No | user / persona |
| content | Text | No | |
| created_at | DateTime | No | |

### Ethnography Domain

**cultural_context_snapshots**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| market_code | String(5) | No | ISO 3166-1 alpha-2: ID / PH / VN; indexed |
| status | String(20) | No | draft / active / archived |
| version | Integer | No | Auto-increments per market per activation |
| signals_json | JSONB | Yes | Structured behavioral signals extracted by LLM |
| raw_sources | JSONB | Yes | [{source, post_count}] |
| quality_score | Float | Yes | 0.0–1.0; threshold 0.5 to activate |
| created_at | DateTime | No | |
| activated_at | DateTime | Yes | Set when status → active |

### Benchmarking Domain

**reproducibility_studies**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| project_id | UUID | No | FK → projects.id, CASCADE |
| source_simulation_id | UUID | No | FK → simulations.id, CASCADE |
| n_runs | Integer | No | Default: 3 (max 5) |
| status | String(50) | No | pending / running / complete / failed |
| sentiment_agreement_rate | Float | Yes | 0.0–1.0 |
| distribution_variance_score | Float | Yes | 0.0–1.0 |
| theme_overlap_coefficient | Float | Yes | 0.0–1.0 |
| confidence_score | Float | Yes | Weighted composite 0.0–1.0 |
| score_breakdown | JSONB | Yes | Per-metric detail |
| created_at | DateTime | No | |
| completed_at | DateTime | Yes | |

**reproducibility_runs**
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | UUID | No | PK |
| study_id | UUID | No | FK → reproducibility_studies.id, CASCADE |
| simulation_id | UUID | No | FK → simulations.id, CASCADE |
| run_index | Integer | No | 1-indexed |
| created_at | DateTime | No | |
