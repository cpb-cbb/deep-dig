# Deep Dig

[English](README.md)

Deep Dig 是一个开源、由 Schema 驱动的浏览器端 AI 文档信息提取工具。系统在后端解析 PDF，
通过可版本化工作流提取带来源依据的结构化数据，并支持导出 Excel 结果。

## 项目能力

- 上传 PDF 文档，并使用 `markitdown` 转换为 Markdown。
- 内置材料属性、自定义字段和实体关系三种工作流。
- 可在界面中定义字段类型，或配置实体类型与关系类型。
- 保存工作流版本、Schema 哈希和任务快照，保证中断续跑结果一致。
- 使用 PostgreSQL、Redis 和 ARQ Worker 管理异步任务。
- 支持数据库多用户注册，任务、Schema、模型设置和加密 API Key 按账号隔离。
- 支持 Anthropic、OpenRouter、OpenAI 兼容接口，以及本地开发用的 fake 模式。
- 可在登录后的设置页配置 Provider、Base URL、模型、API Key 和温度，也可继续读取后端环境变量。
- 查看任务状态、重试和错误，并将完成的任务导出为 `.xlsx`。
- Worker、队列或服务中断后，可手动重新入队尚未完成的文档。
- 不内置套餐、提取额度或单用户任务限流，适合自行部署。
- 模型服务商密钥只保存在后端，不发送到浏览器客户端。

## 架构

```text
PDF
  -> React/Vite 浏览器 Web UI
  -> FastAPI PDF 解析服务（markitdown）
  -> PostgreSQL 任务记录 + Redis 队列
  -> ARQ Worker
  -> 配置的 LLM 服务商
  -> 版本化工作流 + 标准结果外壳
  -> Excel 导出
```

## 目录结构

| 路径                      | 说明                                                                |
| ------------------------- | ------------------------------------------------------------------- |
| `apps/backend`          | FastAPI API、PDF 解析器、ARQ Worker、SQLAlchemy 模型和 Alembic 迁移 |
| `apps/desktop`          | 主业务 React + Vite Web UI，历史目录名为`desktop`                 |
| `apps/web`              | 独立的 React + Vite 营销站点                                        |
| `packages/workflows`    | 服务端工作流定义                                                    |
| `packages/shared-types` | 自动生成的 TypeScript API 类型                                      |
| `infra`                 | 部署及数据库相关资源                                                |
| `docs`                  | 架构、API、开发和运维文档                                           |

## 环境要求

- Node.js 与 pnpm 9
- Python 3.12 或更高版本
- [`uv`](https://docs.astral.sh/uv/)
- PostgreSQL
- Redis

仓库声明的包管理器版本为 `pnpm@9.15.0`。

PostgreSQL 是外部依赖：本仓库不会自动安装或启动它。请先使用操作系统的包管理器或
[PostgreSQL 官方安装程序](https://www.postgresql.org/download/)完成安装，并确保服务正在运行。
macOS 使用 Homebrew 时可以执行：

```bash
brew install postgresql@16
brew services start postgresql@16
```

然后创建本地应用用户和数据库（请自行设置密码）：

```bash
psql postgres
```

```sql
CREATE USER deep_dig WITH PASSWORD 'replace-with-a-local-password';
CREATE DATABASE deep_dig OWNER deep_dig;
\q
```

## 快速开始

### 1. 安装依赖

```bash
git clone <your-repository-url>
cd deep-dig
pnpm install

cd apps/backend
uv sync
cp .env.example .env
```

### 2. 配置后端

使用上面创建的用户名和密码编辑 `apps/backend/.env`：

```env
DATABASE_URL=postgresql+asyncpg://deep_dig:replace-with-a-local-password@localhost:5432/deep_dig
REDIS_URL=redis://localhost:6379/0
AUTH_SECRET=replace-with-a-long-random-secret

LLM_COMPAT_BASE_URL=https://api.openai.com/v1
LLM_COMPAT_API_KEY=replace-with-your-api-key
LLM_COMPAT_MODEL=gpt-4o-mini
```

`AUTH_SECRET` 用于签发登录 Token，并加密各用户保存的 API Key。请生成固定的随机值；用户
保存模型设置后不要再修改。DeepSeek、本地网关等 OpenAI 兼容服务只需替换 URL 和模型名。

执行数据库迁移并创建前端环境文件：

```bash
uv run alembic upgrade head
cd ../..
cp apps/desktop/.env.example apps/desktop/.env
```

公开部署时不要使用示例密钥。

### 3. 启动完整本地环境

在仓库根目录执行：

```bash
pnpm dev:start
```

该命令会启动 Redis、FastAPI API、ARQ Worker 和主 Web UI，但不会安装或启动 PostgreSQL。
执行此命令前，PostgreSQL 必须已经安装、运行并完成配置，否则数据库迁移或 API 启动会失败。

主 Web UI 地址：

```text
http://127.0.0.1:5173
```

本地服务地址：

- Web UI：`http://127.0.0.1:5173`
- API：`http://127.0.0.1:8001`
- API 文档：`http://127.0.0.1:8001/docs`
- Redis：`127.0.0.1:6379`

在主页面选择 **Create account** 创建账号。每个账号分别保存自己的任务、最近 Schema、用户
设置和加密后的 LLM 凭据。需要关闭公开注册时，在 `apps/backend/.env` 中增加
`REGISTRATION_ENABLED=false`，然后重启 API。

从旧版单用户模式升级时，第一次使用原来的 `admin` 和 `LOCAL_AUTH_PASSWORD` 登录。登录成功
后会自动将旧用户及历史任务迁移为数据库账号，之后即可删除该环境变量。

## 开发命令

```bash
# 使用 apps/backend/.env 启动完整本地环境
pnpm dev:start

# 服务管理
pnpm dev:status
pnpm dev:stop
pnpm dev:restart
pnpm dev:logs api
pnpm dev:logs worker

# 只启动主 Web UI
pnpm dev:desktop

# 启动营销站
pnpm dev:web
```

营销站默认运行在 `http://127.0.0.1:5174`。

如需手动启动服务，请分别打开终端：

```bash
# 终端 1：API
cd apps/backend
uv run uvicorn app.main:app --reload --port 8001

# 终端 2：Worker
cd apps/backend
uv run arq app.workers.arq_worker.WorkerSettings

# 终端 3：主 Web UI
cd apps/desktop
pnpm dev
```

## LLM 模式

| 模式                  | 行为                                             |
| --------------------- | ------------------------------------------------ |
| `fake`              | 返回固定演示结果，不调用外部 API，不产生模型费用 |
| `auto`              | 自动使用已配置的可用 Provider                    |
| `openrouter`        | 使用 OpenRouter API                              |
| `anthropic`         | 使用 Anthropic API                               |
| `openai_compatible` | 使用 OpenAI 兼容的`/chat/completions` 接口     |

fake Provider 仍保留给自动化测试和离线开发使用；正常启动流程默认使用 `.env` 中配置的真实
OpenAI 兼容接口。

主界面提供 **Settings** 设置面板。环境变量模式直接读取上述后端配置；自定义模式保存实例级
覆盖配置。API Key 使用由 `AUTH_SECRET` 派生的密钥在后端加密，且不会返回浏览器。

## 数据与隐私

- 上传的 PDF 字节由后端临时处理，应用工作流不会持久化原始 PDF 文件。
- PDF 解析持久缓存默认关闭。仅在显式设置 `PARSED_CACHE_ENABLED=true` 时启用；缓存只保存
  按内容哈希索引的解析文本，不保存上传者文件名。
- 未完成任务的解析文本会临时存在 Redis 和 PostgreSQL 中，以便服务中断后继续处理。文档进入
  完成、失败或取消状态时默认清除；仅启用 `user_settings.store_raw_text` 时长期保留。
- 任务元数据、提取结果、文件名和哈希会根据工作流及用户设置保存。
- Provider 密钥和提取 Prompt 保留在后端。

## 质量检查

```bash
# 后端格式检查、Lint、测试，以及主 Web UI 构建
pnpm check

# 单独构建
pnpm build:desktop
pnpm build:web

# 后端测试
cd apps/backend
uv run pytest
```

修改 API 路由或 Schema 后，请重新生成 OpenAPI 合约和共享 TypeScript 类型：

```bash
pnpm generate:api
```

## 文档

- [架构](docs/architecture.md)
- [后端开发](docs/backend-development.md)
- [主 Web UI 开发](docs/desktop-development.md)
- [API 参考](docs/api-reference.md)
- [开发运行手册](docs/runbooks/development.md)
- [路线图](docs/roadmap.md)

## 贡献与安全

欢迎提交 Pull Request 和 Issue。请勿提交以下内容：

- `.env` 文件或 API 密钥
- 论文 PDF、解析缓存或生成结果
- 数据库备份、Redis 快照或部署凭据

将仓库公开前，请检查部署文档中是否包含私有主机、内部路径或运维凭据，尤其要审查
`docs/runbooks/web-deployment.md`。

## 许可证

Deep Dig 基于 [MIT License](LICENSE) 开源。
