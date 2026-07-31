![logo](./assets/favicon.svg)

# Ollama-Hack V2 🚀

## 📖 简介

> 网上许多暴露无鉴权的 Ollama 接口，想薅来使用，但是一个一个试性能、查模型太麻烦了？还可能要频繁更换失效的接口？
>
> 来试试 Ollama-Hack 吧！它是一个基于 Python 的中转平台，能够帮助你轻松管理、测试和无缝使用多个 Ollama 接口。

Ollama-Hack 是一个用于管理、测试和转发 Ollama API 的服务。它可以集中管理多个 Ollama 端点，并根据性能自动选择最优的线路，提供兼容 OpenAI 的 API。平台提供友好的 Web 界面，方便用户管理端点、模型、API 密钥和用量计划。

## ✨ 功能特性

-   🔄 **多端点管理**：集中管理多个 Ollama 服务端点，可以批量进行导入
    ![端点管理](./assets/endpoints.png)
-   🔍 **端点详情**：查看每个端点的详细信息和可用模型
    ![端点详情](./assets/endpoint_details.png)
-   🧩 **兼容 OpenAI API**：提供兼容 OpenAI 的 API 接口
-   ⚖️ **最优线路选择**：根据 Token/s 性能自动选择最优的 Ollama 端点
-   🔑 **API 密钥管理**：生成和管理用于身份验证的 API 密钥
-   📊 **性能监控**：测试和显示不同端点上模型的性能指标
-   📝 **模型管理**：搜索和查看可用的模型
    ![模型管理](./assets/models.png)
-   📈 **模型性能**：查看每个模型的详细性能数据
    ![模型详情](./assets/model_details.png)
-   🔐 **用户管理**：管理员可以创建和管理用户账户
-   💰 **计划管理**：创建和管理不同的用量计划，限制 API 请求频率
-   🌙 **深色模式**：支持明亮/暗黑主题切换

## 🛠️ 环境要求

-   Docker 和 Docker Compose（推荐）
-   或 Python 3.12+（直接运行）

## 🚀 安装与运行

### 方法一：使用 Docker 部署（推荐）

生产镜像同时包含前端和后端，容器内只运行 Uvicorn。默认 Compose 使用持久化
SQLite 文件，无需额外数据库容器：

```bash
git clone https://github.com/leeflouring/Ollama-Hack.git
cd Ollama-Hack
cp .env.example .env   
docker compose up -d
```

数据保存在当前目录的 `./data/ollama-hack.db`。服务启动后，打开
http://localhost:3000/init 即可使用。

也可以从源码构建同一个镜像：

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

### 方法二：直接运行（开发环境）

#### 后端

```bash
cd backend
# 使用Poetry安装依赖
pip install poetry
poetry install

# 启动服务
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend
# 安装依赖
yarn install

# 开发模式启动
yarn dev
```

## 📝 使用方法

### Web 界面

访问 http://localhost:3000/init 来初始化管理员账户。

登录后，你可以：

-   创建和管理用户账户
-   添加和管理 Ollama 端点
-   生成 API 密钥
-   创建和分配用量计划
-   查看模型性能数据

### 计划管理

V2 版本新增了计划管理功能，管理员可以创建不同的用量计划，并将其分配给用户。每个计划可以设置：

-   每分钟请求限制 (RPM)
-   每天请求限制 (RPD)
-   默认计划标记

### API 使用示例

#### 兼容 Ollama API

```bash
curl -N -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "llama3",
    "messages": [
      {"role": "system", "content": "你是一个有帮助的助手"},
      {"role": "user", "content": "你好，请介绍一下自己"}
    ],
    "temperature": 0.7,
    "stream": true
  }'
```

Ollama-Hack 支持 Ollama 的全部 OpenAI 兼容 API，详细列表请参考：[Ollama/OpenAI Compability](https://github.com/ollama/ollama/blob/main/docs/openai.md)。

## 🔧 配置选项

### 环境变量

应用支持 SQLite、PostgreSQL 和 MySQL。默认 SQLite 配置如下：

```yaml
environment:
    - APP__ENV=prod # 环境类型：dev 或 prod
    - APP__LOG_LEVEL=INFO # 日志级别
    - APP__SECRET_KEY=change_this_key # JWT密钥
    - APP__ACCESS_TOKEN_EXPIRE_MINUTES=30 # 访问令牌过期时间
    - DATABASE__ENGINE=sqlite
    - DATABASE__DB=/data/ollama-hack.db
```

使用外部 PostgreSQL：

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

现有 MySQL 配置继续兼容：

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

应用启动时会创建缺失的表和声明式索引。大型现有数据库首次升级时，创建索引可能
短暂锁表，建议安排维护窗口。应用不会在 SQLite、PostgreSQL 和 MySQL 之间自动
迁移或复制数据；切换数据库前请自行完成备份和迁移。

### 外部端点源（可选）

可以选择从
[Awesome-Ollama-Server](https://github.com/forrany/Awesome-Ollama-Server)
的公开 JSON 数据源自动发现端点。此功能默认关闭：

```dotenv
APP__EXTERNAL_FEED_ENABLED=true
APP__EXTERNAL_FEED_URL=https://raw.githubusercontent.com/forrany/Awesome-Ollama-Server/main/public/data.json
APP__EXTERNAL_FEED_INTERVAL_HOURS=10
```

使用 Docker Compose 时，将 `.env.example` 复制为 `.env` 后修改以上配置即可。
启用后，应用会在启动后及指定间隔下载数据源，只添加尚不存在的 HTTP/HTTPS
端点，并使用本地测试流程重新获取状态、模型和性能；不会信任上游的这些字段，
也不会更新、删除现有端点或覆盖自定义名称。导入后会向新端点发起测试请求，因此
会产生访问第三方服务器的出站网络流量。关闭开关只停止后续同步，已经导入的端点
仍由本地管理员正常管理。

## ⚡ 性能优化对比

以下数据对比改造前后的同一代码路径，统计的是 SQL 语句数而非特定硬件上的响应
时间；`N` 表示当前页记录数。百分比只计算被优化的查询部分，避免把测试环境差异
包装成不可靠的耗时提升。

| 场景 | 原项目 | 当前版本 | 改进 |
| --- | --- | --- | --- |
| 端点列表的模型计数和最新任务 | 每条端点执行 3 次查询（`3N`） | 整页固定 3 次聚合查询 | `N=50` 时 `150 → 3`，减少 98% |
| 模型列表的端点计数 | 每个模型执行 2 次查询（`2N`） | 整页固定 1 次聚合查询 | `N=50` 时 `100 → 1`，减少 99% |
| API Key 近 30 天统计 | 5 次汇总 + 30 次逐日查询，共 35 次 | 1 次条件汇总 + 1 次按日分组，共 2 次 | 统计查询减少 94.3% |
| 单进程数据库连接上限 | 默认 `50 + 100 = 150` | 默认 `5 + 10 = 15`，可通过环境变量调整 | 峰值连接占用降低 90% |
| Docker 运行结构 | 前端、后端分别构建和运行 | 单个非 root Uvicorn 镜像同时提供 API 与静态页面 | 本地构建的最终镜像约 67.5 MiB |

查询计数测试会持续约束这些结果：端点列表总 SQL 数不超过 5，模型关联计数固定
为 1，API Key 统计（含权限查询）总 SQL 数不超过 4。SQLite、PostgreSQL 和
MySQL 均已通过容器启动及建表冒烟测试。

### GitHub 自动构建镜像

仓库包含 `.github/workflows/docker-build.yml`。代码推送到 `main`、`master`、
`workflow-dev` 或 `dev`，或推送 `v*.*.*` 标签后，GitHub Actions 会自动构建
`linux/amd64` 与 `linux/arm64` 的统一镜像，并始终发布到 GHCR。

GHCR 使用仓库自带的 `GITHUB_TOKEN`，无需额外配置。如需同时发布到 DockerHub，
在仓库的 Actions Secrets 中配置 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_TOKEN`
即可。也可以从 Actions 页面手动触发该工作流。

## 👤 作者

[Timlzh](https://github.com/timlzh)

## 📜 许可证

MIT License

## 🖼️ 截图

-   主页
    ![主页](./assets/index.png)
-   端点管理
    ![端点管理](./assets/endpoints.png)
-   模型管理
    ![模型管理](./assets/models.png)
-   模型详情
    ![模型详情](./assets/model_details.png)
-   端点详情
    ![端点详情](./assets/endpoint_details.png)
