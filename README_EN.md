![logo](./assets/favicon.svg)

**English** | [简体中文](./README.md)

# Ollama-Hack V2 🚀

## 📖 Introduction

> Managing exposed, unauthenticated Ollama endpoints one by one is tedious:
> models differ, performance varies, and endpoints can disappear at any time.
>
> Ollama-Hack is a Python-based gateway that manages, tests, and transparently
> uses multiple Ollama endpoints from one place.

Ollama-Hack manages, tests, and forwards Ollama APIs. It automatically selects
healthy, high-performance routes, exposes OpenAI-compatible APIs, and provides
a web interface for endpoints, models, API keys, users, and usage plans.

## ✨ Features

-   🔄 **Multi-endpoint management**: centrally manage and batch-import Ollama endpoints
    ![Endpoint management](./assets/endpoints.png)
-   🔍 **Endpoint details**: inspect endpoint health and available models
    ![Endpoint details](./assets/endpoint_details.png)
-   🧩 **OpenAI-compatible API**: use Ollama through familiar OpenAI endpoints
-   ✅ **Availability filters**: filter endpoint and model lists by all, available, or unavailable
-   ⚖️ **Smart routing and failover**: route only through available endpoint/model pairs, rank them by TPS, and try the next route on failure
-   🔑 **API key management**: create and manage authentication keys
-   📊 **Performance monitoring**: test and display endpoint/model performance
-   📝 **Model management**: search and inspect discovered models
    ![Model management](./assets/models.png)
-   📈 **Model performance**: view detailed performance data for each model
    ![Model details](./assets/model_details.png)
-   🔐 **User management**: create and manage user accounts
-   💰 **Plans and quotas**: configure request limits and assign usage plans
-   🌙 **Dark mode**: switch between light and dark themes

## 🛠️ Requirements

-   Docker and Docker Compose (recommended)
-   Or Python 3.12+ for direct development

## 🚀 Installation and Running

### Option 1: Docker (recommended)

The production image contains both frontend and backend and runs only Uvicorn.
The default Compose configuration uses a persistent SQLite file and requires no
separate database container:

```bash
git clone https://github.com/leeflouring/Ollama-Hack.git
cd Ollama-Hack
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up -d
```

Data is stored in `./data/ollama-hack.db`. After startup, open
http://localhost:3000/init to initialize the administrator account.

To build the same unified image locally:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

The production entry point is covered by a fresh-process import regression and
a live-container startup smoke test, preventing test module caches from hiding
deployment-only circular imports.

### Option 2: Direct development

#### Backend

```bash
cd backend
pip install poetry
poetry install
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
yarn install
yarn dev
```

## 📝 Usage

### Web interface

Open http://localhost:3000/init to initialize the administrator account.
After signing in, you can:

-   Create and manage users
-   Add and manage Ollama endpoints
-   Generate API keys
-   Create and assign usage plans
-   Inspect model availability and performance

### Plan management

Plans can be assigned to users and define:

-   Requests per minute (RPM)
-   Requests per day (RPD)
-   Whether the plan is the default

### Availability filters and smart routing

Endpoint and model lists support **All / Available / Unavailable** filters.
The BaseURL collection in model details also supports **All / ≥ 10 / ≥ 20 /
≥ 30 TPS**. Thresholds are inclusive and applied before pagination. Routable
BaseURLs appear first, with descending measured TPS inside each availability
group.

For requests made through the Ollama or OpenAI-compatible APIs, the gateway
requires both the endpoint and its model link to be available. It selects up to
10 candidates by descending TPS and tries them sequentially. A failure before
the response starts moves to the next candidate. Once a streaming response has
started, already-emitted content is not replayed through another endpoint.

### API example

#### OpenAI-compatible API

```bash
curl -N -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "llama3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello! Please introduce yourself."}
    ],
    "temperature": 0.7,
    "stream": true
  }'
```

Ollama-Hack supports Ollama's OpenAI-compatible APIs. See the
[Ollama OpenAI compatibility documentation](https://github.com/ollama/ollama/blob/main/docs/openai.md)
for the current endpoint list.

## 🔧 Configuration

### Environment variables

SQLite, PostgreSQL, and MySQL are supported. The default SQLite setup is:

```yaml
environment:
    - APP__ENV=prod # dev or prod
    - APP__LOG_LEVEL=INFO
    - APP__SECRET_KEY=change_this_key # JWT secret
    - APP__ACCESS_TOKEN_EXPIRE_MINUTES=30
    - DATABASE__ENGINE=sqlite
    - DATABASE__DB=/data/ollama-hack.db
```

See [`.env.example`](./.env.example) for the complete variable list and example values.

External PostgreSQL:

```yaml
environment:
    - DATABASE__ENGINE=postgresql
    - DATABASE__HOST=postgres
    - DATABASE__PORT=5432
    - DATABASE__USERNAME=ollama_hack
    - DATABASE__PASSWORD=change_this_password
    - DATABASE__DB=ollama_hack
    - DATABASE__POOL_SIZE=5
    - DATABASE__MAX_OVERFLOW=10
```

Existing MySQL deployments remain supported:

```yaml
environment:
    - DATABASE__ENGINE=mysql
    - DATABASE__HOST=mysql
    - DATABASE__PORT=3306
    - DATABASE__USERNAME=ollama_hack
    - DATABASE__PASSWORD=change_this_password
    - DATABASE__DB=ollama_hack
    - DATABASE__POOL_SIZE=5
    - DATABASE__MAX_OVERFLOW=10
```

At startup, the application creates missing tables and declared indexes.
Creating indexes for a large existing database may briefly lock tables, so use
a maintenance window. Data is not automatically migrated between SQLite,
PostgreSQL, and MySQL; back up and migrate it before changing engines.

### External endpoint discovery (optional)

Endpoints can be discovered from the public JSON feed maintained by
[Awesome-Ollama-Server](https://github.com/forrany/Awesome-Ollama-Server).
The built-in application default is disabled, while the bundled `.env.example`
enables it for an out-of-the-box deployment. Set
`APP__EXTERNAL_FEED_ENABLED=false` if it is not wanted:

```dotenv
APP__EXTERNAL_FEED_ENABLED=true
APP__EXTERNAL_FEED_URL=https://raw.githubusercontent.com/forrany/Awesome-Ollama-Server/main/public/data.json
APP__EXTERNAL_FEED_INTERVAL_HOURS=10
```

When enabled, the application downloads the feed after startup and at the
configured interval. It adds only new HTTP/HTTPS endpoints and independently
retests their status, models, and performance. Upstream status, models, TPS,
and timestamps are never trusted. Existing endpoints are not renamed, updated,
or deleted. Importing causes outbound requests to third-party servers. Disabling
the feed stops future synchronization but does not remove endpoints already
imported.

## ⚡ Performance Improvements

The figures below compare SQL statement counts for the same code paths rather
than hardware-dependent response times. `N` is the number of records on the
current page. Percentages apply only to the optimized query work.

| Scenario | Original project | Current version | Improvement |
| --- | --- | --- | --- |
| Model counts and latest task on the endpoint list | 3 queries per endpoint (`3N`) | 3 aggregate queries per page | At `N=50`, `150 → 3` (98% fewer) |
| Endpoint counts on the model list | 2 queries per model (`2N`) | 1 aggregate query per page | At `N=50`, `100 → 1` (99% fewer) |
| API key statistics for the last 30 days | 5 summaries + 30 daily queries (35 total) | 1 conditional summary + 1 daily grouping (2 total) | 94.3% fewer statistic queries |
| Maximum database connections per process | Default `50 + 100 = 150` | Default `5 + 10 = 15`, configurable by environment variables | 90% lower peak connection capacity |
| Docker runtime layout | Separate frontend and backend builds/containers | One non-root Uvicorn image serves API and static UI | Final local build is about 67.5 MiB |
| Model request routing | Did not also validate aggregate endpoint health | Double availability check, TPS ranking, sequential failover | Skips known-unavailable routes and reduces first-choice failures |

Query-count tests enforce these bounds: at most 5 SQL statements for the
endpoint list, exactly 1 model-association count query, and at most 4 statements
for API key statistics including authorization. SQLite, PostgreSQL, and MySQL
have passed container startup and schema-creation smoke tests.

### Automatic GitHub image builds

The repository includes `.github/workflows/docker-build.yml`. Pushes to
`main`, `master`, `workflow-dev`, or `dev`, and `v*.*.*` tags, automatically
build the unified image for `linux/amd64` and `linux/arm64` and always publish
it to GHCR.

GHCR uses the repository's built-in `GITHUB_TOKEN`. To also publish to
Docker Hub, configure the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` Actions
secrets. The workflow can also be started manually from the Actions page.

## 👤 Author

[Timlzh](https://github.com/timlzh)

## 📜 License

MIT License

## 🖼️ Screenshots

-   Dashboard
    ![Dashboard](./assets/index.png)
-   Endpoint management
    ![Endpoint management](./assets/endpoints.png)
-   Model management
    ![Model management](./assets/models.png)
-   Model details
    ![Model details](./assets/model_details.png)
-   Endpoint details
    ![Endpoint details](./assets/endpoint_details.png)
