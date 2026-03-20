---
name: readme-generator
description: >
  Generate a production-quality, copy-paste-ready README.md for any GitHub repository.
  Trigger whenever the user provides a GitHub repository URL and asks for a README,
  documentation, or repo overview. Trigger phrases include: "generate a readme",
  "write docs for my project", "create a readme for this github link", "document this repo",
  "explain this codebase", "document my API", "help me document", "write documentation for",
  "make a readme", "readme for this", "document this". Also trigger when the user pastes
  any GitHub URL (github.com or a GitHub Enterprise domain) alongside any of: "readme",
  "docs", "document", "explain", "write", "generate". Also trigger on a bare GitHub URL
  with no surrounding text — assume README generation is the intent.
  The output is a fully-formed, professional Markdown (.md) file, ready to paste directly
  into GitHub's README section with zero editing required.
---

# README Generator Skill

Given a GitHub repository URL, this skill performs a deep, structured, context-efficient
analysis of the codebase and generates a production-quality README.md — complete with a
Quick Start guide, step-by-step run instructions, architecture diagrams, full API reference,
ENV setup, data models, and workflow diagrams. Output is accurate, hallucination-resistant,
and immediately usable.

---

## CRITICAL RULE — PURE MARKDOWN ONLY

**The entire README output must be 100% pure GitHub-Flavored Markdown. No exceptions.**

The only HTML permitted is the `<div align="center">` wrapper at the very top of the file
(for badge centering). Everything else must use Markdown syntax.

**FORBIDDEN — never use these in the README body:**

| Do NOT write | Write this instead |
|---|---|
| `<br>` or `<br/>` | blank line between paragraphs |
| `<p>text</p>` | plain paragraph text |
| `<b>text</b>` | `**text**` |
| `<i>text</i>` | `*text*` |
| `<code>text</code>` | `` `text` `` |
| `<pre>code</pre>` | fenced code block with ` ``` ` |
| `<ul><li>` / `<ol><li>` | `- item` / `1. item` |
| `<table><tr><td>` | Markdown pipe table `\| col \| col \|` |
| `<h1>` through `<h6>` | `#` through `######` headings |
| `<a href="url">text</a>` | `[text](url)` |
| `<img src="url">` | `![alt text](url)` |
| `<strong>`, `<em>`, `<span>` | Markdown `**bold**`, `*italic*`, plain text |
| `<details>`, `<summary>` | heading + normal prose |
| `&nbsp;` `&gt;` `&lt;` `&#...;` | actual character or avoid entirely |

If you find yourself writing any HTML tag: stop, and use the Markdown equivalent.

**Pre-output HTML check (mandatory):** Before saving the file, scan the full output.
If any HTML tag appears outside the `<div align="center">` header block, rewrite it
in Markdown before saving. Do not skip this check.

---

## Step 0 — Gather Input

Collect from the user:

- **Repository URL** (required) — supports `https://github.com/owner/repo` and GitHub
  Enterprise URLs like `https://github.company.com/owner/repo`
- **Branch** (optional — default: try `main`, fallback `master`, then `develop`)

Parse `{owner}`, `{repo}`, and `{host}` from the URL immediately.
For GitHub Enterprise use: `https://{host}/api/v3/repos/{owner}/{repo}/...`

**If an existing README.md is detected in the file tree**, ask the user:
> "I found an existing README. Should I (A) fully regenerate it from scratch, or
> (B) update and improve the existing content?"
Proceed based on their answer before doing any further fetching.

---

## Step 0b — Context Budget

**Hard cap: 25 web_fetch calls total for the entire scan. This is non-negotiable.**

Every fetch must earn its place. Prioritize ruthlessly.

**Summarize as you read:** After reading each file, distill it into a 3–5 line internal
note: purpose, key exports/routes/classes found, any run commands or env vars detected.
Discard the raw content after summarizing. Hold only extracted facts going forward.

**Stop signal — once you can answer all six, stop fetching more files:**

1. What does this project do?
2. What is the full tech stack (runtime, framework, DB, auth, cache)?
3. What are the main modules and their responsibilities?
4. What environment variables are required?
5. What are the exact commands to clone, install, configure, and run this project?
6. What are the API endpoints (if any)?

If all six are answered, additional fetches produce diminishing returns. Stop and write.

---

## Step 1 — Repository Inventory

### 1a. Fetch Full File Tree (Fetch #1)

```
GET https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1
```

Extract every `blob` path. Store the manifest. Count total files.

**Rate limit:** GitHub allows 60 unauthenticated requests/hour. This skill uses max 25.
If any request returns HTTP 403 with `X-RateLimit-Remaining: 0`, stop immediately and
tell the user: "GitHub API rate limit reached. Please wait 60 minutes, or provide a
personal access token to continue."

**If truncated** (`"truncated": true` in response): Fall back to per-directory listing
for critical paths only. Count each listing toward the 25-call budget.

**If 404:** Repo is private or branch is wrong. Ask the user to confirm the branch,
make the repo public, or paste key files (manifest, entrypoint, routes, `.env.example`,
`Dockerfile`, `Makefile`) directly into the chat.

**If count > 300:** Activate Strategic Sampling Mode (Step 1e).

### 1b. Classify the Repository (zero fetches — use the manifest only)

Scan the file tree paths for these signal files:

| Signal Files | Classification |
|---|---|
| `package.json` + `next.config.*` | Next.js Web App |
| `package.json` + `express`/`fastify`/`koa` in dep paths | Node.js API |
| `package.json` + `@nestjs/core` visible | NestJS Application |
| `pyproject.toml` or `requirements.txt` + Flask/FastAPI/Django | Python Web API |
| `manage.py` present | Django Project |
| `pyproject.toml` alone, no web framework | Python Library or CLI |
| `*.csproj` / `*.sln` / `Program.cs` | .NET / C# Application |
| `Cargo.toml` | Rust Project |
| `go.mod` | Go Service |
| `pom.xml` / `build.gradle` / `build.gradle.kts` | Java / Kotlin / Spring |
| `pubspec.yaml` | Flutter / Dart |
| `mix.exs` | Elixir / Phoenix |
| `*.ipynb` / `train.py` / `model.py` | ML / Data Science |
| Multiple `package.json` at different depths | Monorepo |
| `functions/` + `firebase.json` | Firebase / Serverless |
| Only `*.tf` / `Chart.yaml` / `playbook.yml`, no app code | Infrastructure-only |

Record the classification — it drives file prioritization and which README sections apply.

### 1c. Prioritized Fetch Plan (Fetches #2–#12)

Fetch in strict priority order. After each Tier 1 fetch, check the stop signal (Step 0b).
Stop fetching the moment all six questions are answered.

**Tier 1 — Always fetch:**
1. Primary dependency manifest: `package.json` / `pyproject.toml` / `Cargo.toml` /
   `go.mod` / `pom.xml` / `*.csproj` / `mix.exs` / `pubspec.yaml`
   — also check for lock files for precise versions:
   `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`, `Cargo.lock`
2. `.env.example` / `.env.sample` / `.env.template`
3. Primary entrypoint: `main.*`, `app.*`, `index.*`, `server.*`, `Program.cs`, `cli.*`,
   `manage.py`, `run.py`, `start.py` — at root or `src/` level
4. `Makefile` or `justfile` or `taskfile.yml` — critical for run command detection
5. Schema / API spec: `schema.prisma` / `openapi.yaml` / `swagger.yaml` / `*.graphql`
   — if OpenAPI/Swagger found, use it as sole API Reference source; skip route scanning

**Tier 2 — Fetch if stop signal not yet satisfied:**
6. `Dockerfile` — read `CMD` and `ENTRYPOINT` lines for production start command
7. `docker-compose.yml` — read `command:` fields per service for dev start commands
8. `.github/workflows/` — pick the main CI file; look for `run:` steps confirming
   how the project is built and started in CI
9. Route or controller index files
10. One representative file per major source directory

**Tier 3 — Only if questions remain:**
11. Config files: `next.config.*`, `vite.config.*`, `app.config.*`
12. Additional route files if API surface is still unclear

Use raw file fetch for all content:
```
GET https://raw.githubusercontent.com/{host}/{owner}/{repo}/{branch}/{filepath}
```

**File reading heuristic:** For files > 200 lines, read first 100 lines + last 50 lines.
Summarize immediately. Do not hold full file content in working memory.

### 1d. Targeted Directory Scan (Fetches #13–#20)

For each named source directory that still has unanswered questions:

1. Fetch directory listing: `https://api.github.com/repos/{owner}/{repo}/contents/{path}`
   (1 fetch — use listing to pick 1 file)
2. From the listing, pick the most informative file:
   `index.*` > `*.controller.*` > `*.service.*` > `*.model.*` > `*.router.*` > largest file
3. Read it. Summarize. Move on. One file per directory is enough.

### 1e. Strategic Sampling Mode (300+ file repos)

- Always read: all Tier 1 files, root configs, files up to 2 levels deep in
  `src/`, `app/`, `api/`, `server/`, `backend/`
- Sample: one representative file per subdirectory
- Skip entirely:
  `node_modules/`, `vendor/`, `.venv/`, `.virtualenv/`, `dist/`, `build/`, `target/`,
  `__pycache__/`, `.next/`, `.nuxt/`, `out/`, `coverage/`, `.nyc_output/`,
  `.pytest_cache/`, `.mypy_cache/`, `generated/`, `proto/`, `pb/`,
  all binary assets: `*.png`, `*.jpg`, `*.gif`, `*.ico`, `*.woff`, `*.ttf`,
  `*.eot`, `*.mp4`, `*.mp3`, `*.lock`, `*.min.js`, `*.min.css`, `*.map`, `*.snap`

---

## Step 2 — Deep Analysis Phase

Do not begin writing the README yet. Build the complete internal model from your notes.

### 2a. Tech Stack Extraction

Only document technologies confirmed in files you actually read.

**Runtime version detection (priority order):**
- Node: `engines.node` in package.json → `.nvmrc` → `.node-version`
- Python: `python_requires` in pyproject.toml → `.python-version` → `runtime.txt`
- Go: first line of `go.mod`
- Java/Kotlin: `<java.version>` in pom.xml → `sourceCompatibility` in build.gradle
- .NET: `<TargetFramework>` in `*.csproj`
- Elixir: `elixir:` in `mix.exs`
- Flutter: `environment.sdk` in `pubspec.yaml`

**Framework detection from dependency names:**
Web: Next.js, React, Vue, Angular, Svelte, Express, Fastify, Koa, NestJS, Hapi,
Flask, FastAPI, Django, Spring Boot, Gin, Echo, Fiber, Rails, Laravel, Phoenix,
ASP.NET Core, Blazor

ORM: Prisma, TypeORM, Sequelize, Drizzle, SQLAlchemy, Hibernate, GORM, ActiveRecord,
Entity Framework Core, Ecto

Testing: Jest, Vitest, Mocha, Pytest, JUnit, Go test, RSpec, PHPUnit, xUnit, NUnit

Use lock file versions. `"express": "^4.18.0"` in package.json → check package-lock.json
for the resolved `4.18.2`. Always prefer lock file precision over manifest ranges.

### 2b. Environment Variable Detection

Three-source sweep. For each variable found, record: name, required/optional, category,
description (from variable name, comments, and usage context).

**Source 1 — `.env.example` / `.env.sample`:**
Every `KEY=value` line → extract key. Comment lines directly above a key = its description.

**Source 2 — Config files:**
`${ENV_VAR}` in YAML/JSON, Spring Boot `application.properties` `${VAR}` placeholders,
.NET `appsettings.json` + `builder.Configuration["VAR"]`,
Elixir `System.get_env("VAR")` in `config/runtime.exs`,
config object chaining: trace `config.database.url` back to its env var origin.

**Source 3 — Source code scanning (when no .env.example exists):**

| Language | Patterns |
|---|---|
| JS / TS | `process.env.VAR`, `process.env['VAR']` |
| Python | `os.getenv('VAR')`, `os.environ['VAR']`, `os.environ.get('VAR')` |
| Go | `os.Getenv("VAR")` |
| Java | `System.getenv("VAR")`, `@Value("${var}")` |
| Kotlin | `System.getenv("VAR")`, `environment["VAR"]` |
| Ruby | `ENV['VAR']`, `ENV.fetch('VAR')` |
| C# / .NET | `Environment.GetEnvironmentVariable("VAR")` |
| Elixir | `System.get_env("VAR")`, `System.fetch_env!("VAR")` |
| Rust | `std::env::var("VAR")`, `env::var("VAR")` |

Mark Source 3 variables: `*(detected from source code)*`

### 2c. API Endpoint Detection

If OpenAPI/Swagger spec found in Tier 1: use it as the sole source. Skip route scanning.

Otherwise scan route and controller files for these patterns:

**Node.js / Express / Fastify / Koa:**
`app.get(`, `app.post(`, `router.get(`, `router.post(`, `router.put(`,
`router.patch(`, `router.delete(`, `fastify.get(`, `fastify.post(`, `fastify.register(`

**NestJS:**
`@Controller(`, `@Get(`, `@Post(`, `@Put(`, `@Patch(`, `@Delete(`, `@UseGuards(`

**Python FastAPI / Flask:**
`@app.get(`, `@app.post(`, `@router.get(`, `@router.post(`, `@blueprint.route(`

**Django:**
`path(`, `re_path(`, `include(`, `router.register(`, `url(`

**Java / Kotlin / Spring:**
`@GetMapping`, `@PostMapping`, `@PutMapping`, `@PatchMapping`, `@DeleteMapping`,
`@RequestMapping`

**Go:**
`router.HandleFunc(`, `r.GET(`, `r.POST(`, `e.GET(`, `e.POST(`,
`chi.Get(`, `chi.Post(`, `mux.Handle(`

**C# / ASP.NET Core:**
`[HttpGet]`, `[HttpPost]`, `[HttpPut]`, `[HttpPatch]`, `[HttpDelete]`,
`app.MapGet(`, `app.MapPost(`

**tRPC:**
`createTRPCRouter(`, `publicProcedure.query(`, `protectedProcedure.mutation(`

**GraphQL:**
`type Query {`, `type Mutation {`, `type Subscription {` in `.graphql` files and resolvers

For each endpoint extract: HTTP method, path, handler name → infer description,
middleware/guards applied. Mark uncertain shapes: `*(schema inferred — verify)*`

### 2d. Module Summarization

For every major source directory encountered, write a 1–2 sentence summary before
writing the README. These feed directly into Project Structure and Architecture.

Format: `{directory}/  →  {primary responsibility} — {key patterns observed}`

```
src/routes/        → HTTP routing; maps paths to controller handlers
src/controllers/   → Request handlers; validate input, call services, return responses
src/services/      → Business logic; orchestrates data access and external integrations
src/repositories/  → Data access layer; wraps DB queries, returns domain objects
src/domain/        → Core entities and value objects (Clean Architecture)
src/ports/         → Interface contracts for adapters (Hexagonal Architecture)
src/adapters/      → Concrete implementations: DB, external APIs, file system
src/middleware/    → Cross-cutting: auth guards, rate limiting, logging, error handling
src/config/        → Environment parsing and application configuration bootstrap
src/utils/         → Pure utility functions with no side effects
src/events/        → Event definitions and handlers
src/commands/      → CQRS command handlers and command bus
src/queries/       → CQRS query handlers and read models
```

### 2e. Architecture Inference

Fill this table before generating any diagram. Mark unknowns as "unclear — omit from docs."

| Question | Answer |
|---|---|
| Application type | API / Web app / CLI / Library / ML pipeline / Monorepo / Infrastructure |
| Architecture style | Monolith / Layered MVC / Clean Architecture / Hexagonal / DDD / Microservices / Serverless / Event-driven / CQRS / Event Sourcing |
| Primary entry point | `{file}` → `{function or class}` |
| Request lifecycle | `Client → [Auth MW] → Router → Controller → Service → Repository → DB` |
| Background jobs | Present/Absent — if present: queue system name + job types |
| External integrations | Every third-party API or service called |
| Data persistence | Primary DB + ORM + cache layer |
| Auth mechanism | JWT / OAuth2 / Session / API Key / mTLS / None |

**Architecture detection signals:**
- `domain/`, `application/`, `infrastructure/`, `interfaces/` → Clean Architecture
- `ports/`, `adapters/`, `core/` → Hexagonal
- `commands/`, `queries/`, `handlers/`, `read-models/` → CQRS
- `events/`, `event-store/`, `aggregates/`, `projections/` → Event Sourcing
- Separate deployable services each with own manifest + Dockerfile → Microservices
- `serverless.yml` / `sam.yaml` / `cdk.ts` → Serverless
- Kafka / RabbitMQ / NATS as primary communication → Event-driven

### 2f. Run Command Detection — CRITICAL STEP

**This is the most important analysis step for Getting Started accuracy.**
Produce the exact sequence of commands any developer needs to go from a fresh machine
to a running local instance. Extract from actual files — never invent commands.

Build this structured note from what you find:

```
INSTALL:      {exact dependency install command}
ENV_SETUP:    cp .env.example .env   (or "no .env.example found")
DB_SETUP:     {exact migration/setup command, or "none"}
SEED:         {exact seed command, or "none"}
DEV_RUN:      {exact development start command}
PROD_BUILD:   {exact build command, or "same as dev"}
PROD_RUN:     {exact production start command}
DOCKER_RUN:   docker-compose up --build   (or "no docker-compose found")
WORKER:       {exact worker start command, or "none"}
TEST:         {exact test command, or "none"}
LINT:         {exact lint command, or "none"}
EXPECTED_OUTPUT: {what the user should see in terminal when app starts successfully}
```

If a command cannot be found from any source: mark it `NOT_FOUND`.
A missing command is better than an invented one.

**Step 2 — Install: detect from these signals in priority order:**

| Signal | Install Command |
|---|---|
| `pnpm-lock.yaml` present | `pnpm install` |
| `yarn.lock` present | `yarn install` |
| `package.json` present (no yarn/pnpm lock) | `npm install` |
| `requirements.txt` present | `pip install -r requirements.txt` |
| `pyproject.toml` + `poetry.lock` | `poetry install` |
| `pyproject.toml` alone | `pip install -e .` |
| `Cargo.toml` | `cargo build` |
| `go.mod` | `go mod download` |
| `pom.xml` + `mvnw` | `./mvnw install` |
| `pom.xml` only | `mvn install` |
| `build.gradle` + `gradlew` | `./gradlew build` |
| `Gemfile` | `bundle install` |
| `pubspec.yaml` | `flutter pub get` |
| `mix.exs` | `mix deps.get` |
| `*.csproj` | `dotnet restore` |
| `composer.json` | `composer install` |
| `Makefile` has `install` target | `make install` |

**Step 4 — DB Setup: detect from these signals:**

| Signal | Setup Command |
|---|---|
| `schema.prisma` | `npx prisma migrate dev` (dev) / `npx prisma migrate deploy` (prod) |
| `alembic.ini` or Python `migrations/` | `alembic upgrade head` |
| `manage.py` present | `python manage.py migrate` |
| `Makefile` has `migrate` target | `make migrate` |
| Docker Compose has DB service | `docker-compose up -d db` (before running app) |
| .NET + Entity Framework | `dotnet ef database update` |
| `mix.exs` + Ecto | `mix ecto.create && mix ecto.migrate` |
| `db/schema.rb` (Rails) | `rails db:create && rails db:migrate` |

**Step 6 — Dev Run: detection priority order:**

1. `Makefile` → look for `run`, `dev`, `start`, `serve` targets → use `make {target}`
2. `package.json` `scripts` → look for `"dev"`, `"start"`, `"serve"`, `"develop"` keys
3. `docker-compose.yml` → `command:` field of the main app service
4. `Dockerfile` → `CMD` instruction
5. `.github/workflows/` CI `run:` steps → the build/test step reveals the run pattern
6. Framework defaults (use ONLY if nothing found above, and label as convention):

| Framework | Default Dev Command |
|---|---|
| Next.js | `npm run dev` → http://localhost:3000 |
| Vite / React / Vue | `npm run dev` → http://localhost:5173 |
| NestJS | `npm run start:dev` → http://localhost:3000 |
| Express (bare) | `node app.js` or `node server.js` |
| Node.js + nodemon | `nodemon src/index.js` |
| TypeScript + ts-node | `ts-node src/index.ts` |
| Python bare script | `python main.py` or `python app.py` or `python run.py` |
| Flask | `flask run` → http://localhost:5000 |
| FastAPI | `uvicorn main:app --reload` → http://localhost:8000 |
| Django | `python manage.py runserver` → http://localhost:8000 |
| Go | `go run main.go` or `go run cmd/{app}/main.go` or `go run .` |
| Rust | `cargo run` |
| Spring Boot | `./mvnw spring-boot:run` or `./gradlew bootRun` |
| ASP.NET Core | `dotnet run` or `dotnet run --project src/{ProjectName}` |
| Rails | `rails server` → http://localhost:3000 |
| Laravel | `php artisan serve` → http://localhost:8000 |
| Phoenix | `mix phx.server` → http://localhost:4000 |
| Flutter web | `flutter run -d chrome` |

**EXPECTED_OUTPUT:** Determine what text appears in the terminal when startup succeeds.
Common patterns: `Server listening on port 3000`, `Application is running on: http://localhost:3000`,
`Uvicorn running on http://0.0.0.0:8000`, `Started Application in X seconds`,
`[Nest] ... Application is listening on port 3000`.
If detectable from the entrypoint file's logger calls, use the actual message.

---

## Step 3 — Generate the README

Write only after completing Steps 1–2. Replace every `{placeholder}` with real values.
If a section has nothing real to document: omit it entirely. Never use filler text.
Match README depth to project complexity.

**REMINDER: Pure Markdown only. No HTML tags except `<div align="center">` at the top.**

---

### README TEMPLATE

````markdown
<div align="center">

# {emoji} {Project Name}

> {One sentence: what it does and why it matters}

[![License](https://img.shields.io/github/license/{owner}/{repo})](LICENSE)
[![Stars](https://img.shields.io/github/stars/{owner}/{repo}?style=flat)](https://github.com/{owner}/{repo}/stargazers)
[![Issues](https://img.shields.io/github/issues/{owner}/{repo})](https://github.com/{owner}/{repo}/issues)
[![Last Commit](https://img.shields.io/github/last-commit/{owner}/{repo})](https://github.com/{owner}/{repo}/commits)
![{Language}](https://img.shields.io/badge/{Language}-{HexColor}?logo={logo-slug}&logoColor=white)

</div>

---

## ⚡ Quick Start

> Clone, install, and run in under 2 minutes.

```bash
# 1. Clone
git clone https://github.com/{owner}/{repo}.git
cd {repo}

# 2. Install dependencies
{INSTALL from Step 2f}

# 3. Configure environment
cp .env.example .env

# 4. Run
{DEV_RUN from Step 2f}
```

{EXPECTED_OUTPUT from Step 2f — e.g. "Server starts on `http://localhost:3000`"}

> For database setup, environment variable configuration, and Docker instructions,
> see [Getting Started](#-getting-started) below.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Demo](#-demo)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the Project](#running-the-project)
- [API Reference](#-api-reference)
- [Data Models](#-data-models)
- [Workflows & Diagrams](#-workflows--diagrams)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [Security](#-security)
- [License](#-license)

---

## 🌟 Overview

{Paragraph 1: What problem does this solve? Who is it for?}

{Paragraph 2: How does it work at a high level? What is the core technical approach?}

{Paragraph 3 (omit if nothing notable): Key design decisions, trade-offs, or what makes
this different from alternatives.}

---

## 🎬 Demo

{Include ONLY for web apps or CLIs where a screenshot meaningfully shows the project.
Use pure Markdown image syntax — NOT an HTML img tag:}

![{Project Name} screenshot]({path/to/screenshot.png or hosted URL})

> **Live demo:** [{URL}]({URL})

{Omit this entire section if no screenshot path or live URL was found.}

---

## ✨ Features

{Every bullet must be derived from an actual module, route, service, or config found.
Do not list assumed or aspirational features — only what is implemented.}

- **{Feature}** — {what it does, grounded in code you actually read}
- **{Feature}** — {what it does}
- **{Feature}** — {what it does}

---

## 🏗️ Architecture

> {1–2 sentences naming the exact architecture style, e.g.: "Layered MVC REST API on
> NestJS and PostgreSQL following Controller → Service → Repository, with BullMQ for
> async background processing and Redis for response caching."}

```mermaid
flowchart TD
    Client([Client])
    API[{AppName}_API\nport_{PORT}]
    AuthMW[Auth_Middleware]
    Router[Router_Layer]
    Controllers[Controllers]
    Services[Service_Layer]
    Repos[Repository_Layer]
    DB[({Database})]
    Cache[({Cache})]

    Client --> API
    API --> AuthMW --> Router --> Controllers
    Controllers --> Services --> Repos --> DB
    Services --> Cache
```

{Replace all node labels with actual component names from the repository.
Architecture diagram rules — enforce before writing:
  - Node IDs: alphanumeric + underscores ONLY. No spaces. No hyphens as first character.
    Valid: AuthService, DB_Postgres, BullMQ_Queue
    Invalid: "Auth Service", DB-Postgres, 1_Service
  - Every node must be a real component you found in the codebase
  - Max 15 nodes — merge helpers into their parent module
  - Inferred components: label as ComponentName_inferred}

---

## 🛠️ Tech Stack

{Only rows confirmed from manifest files or source code. Use lock file versions.}

| Layer | Technology | Version |
|-------|------------|---------|
| Runtime | {confirmed} | {version} |
| Language | {confirmed} | {version} |
| Framework | {confirmed} | {version} |
| Database | {confirmed} | {version} |
| ORM | {confirmed} | {version} |
| Cache | {confirmed} | {version} |
| Queue | {confirmed} | {version} |
| Auth | {confirmed} | {version} |
| Validation | {confirmed} | {version} |
| Testing | {confirmed} | {version} |
| CI/CD | {confirmed} | — |
| Deployment | {confirmed} | — |

---

## 📁 Project Structure

{Every annotated path must exist in the file tree. No invented directories.}

```
{repo-name}/
├── {actual-folder}/            # {module summary from Step 2d}
│   ├── {actual-subfolder}/     # {what it contains}
│   └── {actual-file.ext}       # {specific purpose}
├── {actual-folder}/            # {module summary}
├── Dockerfile                  # Container image definition
├── docker-compose.yml          # Local multi-service orchestration
├── .env.example                # Environment variable reference
└── {manifest-file}             # Dependency definitions
```

**Module responsibilities:**

| Module | Path | Responsibility |
|--------|------|----------------|
| {Module name} | `{actual/path}` | {summary from Step 2d} |
| {Module name} | `{actual/path}` | {summary} |

---

## 🚀 Getting Started

### Prerequisites

{List every actual prerequisite with version constraints where detectable.}

- **{Technology}** `>= {version}` — *(from `{config-file}`)*
- **{Technology}** — *(required for: {specific reason})*

### Installation

Follow these steps in order. Each must succeed before proceeding to the next.

```bash
# Step 1 — Clone the repository
git clone https://github.com/{owner}/{repo}.git
cd {repo}
```

```bash
# Step 2 — Install dependencies
{INSTALL from Step 2f}
```

```bash
# Step 3 — Set up environment variables
cp .env.example .env
```

Open `.env` in your editor and set the required values.
See [Environment Variables](#environment-variables) below for a full explanation.

```bash
# Step 4 — Initialize the database
{DB_SETUP from Step 2f}
```

{Omit Step 4 block entirely if DB_SETUP is "none"}

```bash
# Step 5 — Seed initial data (optional)
{SEED from Step 2f}
```

{Omit Step 5 block entirely if SEED is "none"}

### Environment Variables

> **Never commit `.env` to version control.** It is already listed in `.gitignore`.

{Every variable from Step 2b. Grouped by category. Required vs optional clearly marked.}

```env
# ── Application ────────────────────────────────────────────────────────────────
NODE_ENV=development                     # development | production | test
PORT=3000                                # Port the server listens on

# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
                                         # Primary DB connection string — REQUIRED

# ── Authentication ─────────────────────────────────────────────────────────────
JWT_SECRET=replace-with-a-long-random-string
                                         # REQUIRED — min 32 chars, never expose
JWT_EXPIRES_IN=7d                        # Token TTL: 15m | 1h | 7d

# ── External Services ──────────────────────────────────────────────────────────
{SERVICE_KEY}=your-key-here              # {which service and what it enables}

# ── Cache ──────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379         # Redis connection string

# ── Optional ───────────────────────────────────────────────────────────────────
LOG_LEVEL=info                           # (Optional) debug | info | warn | error
```

**Required** (app will not start without these): `{list names}`
**Optional** (have defaults, safe to omit locally): `{list names}`

### Running the Project

#### Development — with hot reload

```bash
{DEV_RUN from Step 2f}
```

When startup succeeds, you should see:

```
{EXPECTED_OUTPUT from Step 2f}
```

{Describe what becomes available: e.g. "API available at `http://localhost:3000`"}

#### Production

```bash
# Build (if a separate build step exists)
{PROD_BUILD from Step 2f — omit this block if same as dev or not applicable}

# Start
{PROD_RUN from Step 2f}
```

#### With Docker Compose

> Recommended — starts the app, database, and cache together with no manual setup.

```bash
# Build images and start all services
docker-compose up --build

# Start in background
docker-compose up -d

# Tail logs for the application service
docker-compose logs -f {app-service-name-from-docker-compose}

# Stop everything and remove containers
docker-compose down
```

{What this starts: e.g. "Starts the API on port 3000, PostgreSQL on 5432, Redis on 6379."}

#### Additional commands

{Include only commands that were actually found in the repo:}

```bash
{DB_SETUP}           # Apply database migrations
{WORKER}             # Start background job worker
{LINT}               # Run linter
```

{Omit any line where the command is "none" or "NOT_FOUND"}

---

## 📡 API Reference

{Include ONLY if HTTP/REST/GraphQL/gRPC routes were found in Step 2c.
Omit this section entirely if no routes were detected — do not invent endpoints.}

### Base URL

```
Development:  http://localhost:{PORT}{/api/v1}
Production:   https://{domain}{/api/v1}
```

### Authentication

{Describe actual auth mechanism found in the middleware.}

```
Authorization: Bearer {token}
```

> Obtain a token via `POST /auth/login`. Tokens expire after `{JWT_EXPIRES_IN}`.

---

{One `###` per route group. Every endpoint must be from Step 2c.}

### {Resource — e.g. Authentication}

#### `POST /auth/register`

> {Description inferred from handler name or code comment}

**Request Body**

```json
{
  "email": "string",
  "password": "string",
  "name": "string"
}
```

**Response** `201 Created`

```json
{
  "user": { "id": "uuid", "email": "string" },
  "token": "string"
}
```

**Errors**

| Status | Reason |
|--------|--------|
| `400` | Validation failed |
| `409` | Email already registered |

{If shape is uncertain:}
> *(Schema inferred from repository structure — verify against source before using.)*

---

{Repeat for every route group found in Step 2c.}

---

## 🗄️ Data Models

{Include ONLY if schema.prisma, SQL migrations, or ORM model files were found.
Omit this section entirely if no schema evidence was detected.}

```mermaid
erDiagram
    USER {
        uuid id PK
        string email
        string password_hash
        timestamp created_at
    }
    POST {
        uuid id PK
        string title
        text content
        uuid author_id FK
        timestamp created_at
    }
    USER ||--o{ POST : "authors"
```

{Replace with actual schema. ER field types: string, int, float, boolean, uuid,
timestamp, text only — not PostgreSQL types like varchar(255) or bigint.}

| Model | Table | Key Fields | Description |
|-------|-------|------------|-------------|
| `{ModelName}` | `{table}` | `{pk}`, `{field}` | {what it represents} |

---

## 🔄 Workflows & Diagrams

{Generate 1–4 diagrams for the major flows. More than 4 creates noise.
Node ID rules for ALL diagrams below: alphanumeric + underscores only. No spaces.}

### {Primary Workflow — name it for what it describes}

```mermaid
sequenceDiagram
    actor Client
    participant Router as API_Router
    participant Auth as JWT_Middleware
    participant Ctrl as UserController
    participant Svc as UserService
    participant DB as PostgreSQL

    Client->>Router: POST /api/users
    Router->>Auth: validate token
    alt Token invalid
        Auth-->>Client: 401 Unauthorized
    else Token valid
        Auth->>Ctrl: req + user context
        Ctrl->>Svc: createUser(dto)
        Svc->>DB: INSERT INTO users
        DB-->>Svc: created row
        Svc-->>Ctrl: User entity
        Ctrl-->>Client: 201 Created
    end
```

{Replace with actual component names and actual flow from the repository.}

---

### {Secondary Workflow — e.g. Background Job Processing}

{Include ONLY if a queue or async system was found. Choose diagram type:
stateDiagram-v2 for state machines, flowchart for pipelines,
sequenceDiagram for multi-actor flows. Omit if no async system exists.}

---

### System Component Diagram

```mermaid
classDiagram
    class UserController {
        +register(dto) User
        +login(dto) Token
        +getProfile(id) User
    }
    class UserService {
        +createUser(dto) User
        +validateCredentials(email, password) User
    }
    class UserRepository {
        +findByEmail(email) User
        +create(data) User
    }
    UserController ..> UserService : uses
    UserService ..> UserRepository : uses
```

{Replace with actual classes/modules and methods found in the codebase.
For functional code: represent each module as a "class" node with exported functions.}

---

## 🧪 Testing

{Include ONLY if test files or test config were found. Omit entirely if no tests exist.}

```bash
# Run all tests
{TEST from Step 2f}

# Run with coverage report
{coverage variant}

# Run a single file
{example using an actual test file path}

# Watch mode
{watch variant — omit this line if not found}
```

{If coverage threshold configured:}
> **Coverage threshold:** {X}% — from `{config-file}`

| Type | Location | Framework |
|------|----------|-----------|
| Unit | `{actual path}` | {framework} |
| Integration | `{actual path}` | {framework} |
| E2E | `{actual path}` | {runner} |

---

## 🚢 Deployment

{Only document platforms and commands confirmed in actual files.}

### Docker

```bash
# Build production image
docker build -t {repo-name}:{tag} .

# Run
docker run -d \
  -p {port}:{port} \
  --env-file .env \
  --name {repo-name} \
  {repo-name}:{tag}
```

### {Cloud Platform — only if deploy config was found}

```bash
{exact deploy command from vercel.json / railway.toml / fly.toml / render.yaml}
```

### CI/CD Pipeline

{From actual `.github/workflows/*.yml`:}

```
{trigger event}
  └── {job 1}
  └── {job 2}
  └── {deploy job}  (main branch only)
```

> **Required GitHub Secrets:** `{SECRET}`, `{SECRET}`

---

## ❓ Troubleshooting

{Include ONLY if real issues are detectable: complex setup, peer dependency warnings,
unusual port conflicts, config gotchas, or TODO/FIXME in setup-related files.}

**{Specific issue — e.g. "Database connection refused at startup"}**

Cause: {why, from code evidence}

Fix:

```bash
{diagnostic or fix command}
```

---

**Port already in use**

Set a different port in your `.env`:

```env
PORT=3001
```

---

{Omit this section entirely if no real issues are apparent from the code.}

---

## 🤝 Contributing

Contributions are welcome. Here is how:

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature-name`
3. Commit using [Conventional Commits](https://conventionalcommits.org/):
   `git commit -m 'feat: describe your change'`
4. Push: `git push origin feature/your-feature-name`
5. Open a Pull Request targeting `main`

{If lint/format config found (.eslintrc, .prettierrc, ruff.toml, .editorconfig):}

Make sure these pass before submitting:

```bash
{LINT}
{TYPECHECK — omit if not found}
{TEST}
```

{If CONTRIBUTING.md exists: "See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines."}

---

## 🔒 Security

{If SECURITY.md exists:}
See our [Security Policy](SECURITY.md) for how to report vulnerabilities.

{If no SECURITY.md:}
To report a security vulnerability, do not open a public GitHub issue.
Use [GitHub's private vulnerability reporting](https://github.com/{owner}/{repo}/security/advisories/new)
or contact the maintainer directly.

---

## 📄 License

This project is licensed under the **{License Name}** —
see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built by [{owner}](https://github.com/{owner})

</div>
````

---

## Step 4 — Pre-Output Quality Audit

Fix every failing item before saving the file.

**HTML check — zero tolerance:**
- [ ] Scan entire output: any HTML tags outside `<div align="center">`?
- [ ] No `<br>`, `<p>`, `<table>`, `<img>`, `<b>`, `<i>`, `<code>`, `<pre>`, `<ul>`,
  `<li>`, `<a>`, `<h1>`–`<h6>`, `<span>`, `<div>`, `<details>`, `<summary>` in body
- [ ] No HTML entities (`&nbsp;`, `&gt;`, `&lt;`, `&#...;`) in body text
- [ ] All images use `![alt](url)` Markdown syntax
- [ ] All links use `[text](url)` Markdown syntax
- [ ] All tables use Markdown pipe syntax — not HTML table tags

**Run commands — accuracy:**
- [ ] Quick Start block shows a clean 4–5 line sequence from clone to running
- [ ] Every command was found in an actual file (manifest, Makefile, Dockerfile,
  docker-compose, CI workflow) — not invented from guesswork
- [ ] Install command matches the lockfile present (npm/yarn/pnpm; pip/poetry)
- [ ] Dev run command is the correct one for this specific project
- [ ] DB setup step present if migration system was found, absent if not
- [ ] EXPECTED_OUTPUT line tells user what successful startup looks like in the terminal
- [ ] Docker Compose section names the actual service from docker-compose.yml

**Accuracy — zero tolerance:**
- [ ] Zero `{placeholder}` values remain in the output
- [ ] Every endpoint was confirmed in Step 2c — none invented
- [ ] Every env var was confirmed in Step 2b — none invented
- [ ] Every technology in the stack table confirmed in a manifest or source file
- [ ] Uncertain items marked `*(inferred — verify against source)*`
- [ ] No section contains generic filler

**Diagrams — syntax validity:**
- [ ] Every diagram opens with valid declaration: `flowchart TD`, `sequenceDiagram`,
  `erDiagram`, `classDiagram`, `stateDiagram-v2`, `graph LR`
- [ ] All node IDs: alphanumeric + underscores ONLY — no spaces, no hyphens as first char
- [ ] All brackets/parentheses properly closed in node labels
- [ ] Arrow directions match actual call flow
- [ ] No diagram exceeds 15 nodes
- [ ] ER field types: only `string`, `int`, `float`, `boolean`, `uuid`, `timestamp`, `text`

**Completeness:**
- [ ] Every major source directory in Project Structure with real annotation
- [ ] All env vars (required + optional) in ENV block, grouped and annotated
- [ ] All route groups have own subsection in API Reference
- [ ] Sections with nothing to document are omitted, not padded
- [ ] README depth matches project complexity

---

## Step 5 — Output

Save as `README_{repo-name}.md` and present with `present_files`.

Tell the user:

> "Here's your production README. Every command was pulled from actual files in the
> repository — nothing invented. The Quick Start gives anyone a zero-to-running path
> in under 2 minutes. Copy the content directly into your GitHub `README.md`.
> All Mermaid diagrams render natively on GitHub."

---

## Edge Cases & Special Handling

**Private repository (404):**
Ask user to make it public, confirm the branch, or paste: manifest, entrypoint,
route files, `.env.example`, `Dockerfile`, `Makefile` directly into the chat.

**GitHub Enterprise URL:**
Use `https://{enterprise-host}/api/v3/repos/{owner}/{repo}/...` for all API calls.
Raw: `https://{enterprise-host}/{owner}/{repo}/raw/{branch}/{filepath}`

**Existing README.md found:**
Ask: "Regenerate from scratch, or update the existing one?" before proceeding.

**Monorepo:**
Ask: "I see packages: {list}. One top-level README covering all, or per-package READMEs?"

**OpenAPI/Swagger spec found:**
Use as sole source for API Reference. Skip route file scanning entirely.

**No `.env.example`:**
Fall back to Source 3 code scanning. Mark all found vars `*(detected from source code)*`.

**Run command not found in any file:**
Document the framework-default command, labeled:
> *(Standard {Framework} convention — verify this is correct for your setup.)*

**No run command found and framework unknown:**
Ask the user directly: "I couldn't find the run command in the repository. What command
do you use to start this project locally?" Add their answer to the README.

**No API routes found:**
Omit API Reference entirely. Never invent routes.

**No tests found:**
Omit Testing section entirely. Never invent test commands.

**ML / Data Science project:**
Replace API Reference with **Model & Training**: dataset format, training command,
hyperparameters from argparse/config files, evaluation metrics, inference usage.

**CLI tool:**
Replace API Reference with **Commands Reference**: every command, subcommand, flag,
and argument from argparse/click/cobra/clap/urfave definitions in the entrypoint.

**Infrastructure-only repo (Terraform, Helm, Ansible):**
Replace Architecture with **Infrastructure Overview** (Mermaid flowchart of resources).
Replace API Reference with **Resources & Modules** from `variables.tf` / `values.yaml`.

**GitHub API rate limit hit mid-scan:**
Stop fetching. Document from what was learned. Add:
> *(README generated from partial scan — rate limit reached. Re-run in 60 minutes.)*

**Non-English repository:**
Generate README in English. Note at the top if the project targets non-English speakers.
