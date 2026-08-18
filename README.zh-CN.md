# Deep Dig

[English](README.md)

Deep Dig 是一个面向材料科学论文的实验性浏览器端 AI 信息提取工具。系统在后端解析 PDF，
根据论文内容和用户指定的属性提取结构化数据，并支持导出 Excel 结果。

## 项目能力

- 上传论文 PDF，并使用 `markitdown` 转换为 Markdown。
- 通过 `material_extraction` 工作流提取材料科学属性。
- 使用 PostgreSQL、Redis 和 ARQ Worker 管理异步任务。
- 支持 Anthropic、OpenRouter、OpenAI 兼容接口，以及本地开发用的 fake 模式。
- 查看任务状态、重试、配额和错误，并将完成的任务导出为 `.xlsx`。
- 模型服务商密钥只保存在后端，不发送到浏览器客户端。

## 架构

```text
PDF
  -> React/Vite 浏览器 Web UI
  -> FastAPI PDF 解析服务（markitdown）
  -> PostgreSQL 任务记录 + Redis 队列
  -> ARQ Worker
  -> 配置的 LLM 服务商
  -> 标准化提取结果
  -> Excel 导出
```

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `apps/backend` | FastAPI API、PDF 解析器、ARQ Worker、SQLAlchemy 模型和 Alembic 迁移 |
| `apps/desktop` | 主业务 React + Vite Web UI，历史目录名为 `desktop` |
| `apps/web` | 独立的 React + Vite 营销站点 |
| `packages/workflows` | 服务端工作流定义 |
| `packages/shared-types` | 自动生成的 TypeScript API 类型 |
| `infra` | 部署及数据库相关资源 |
| `docs` | 架构、API、开发和运维文档 |

## 环境要求

- Node.js 与 pnpm 9
- Python 3.12 或更高版本
- [`uv`](https://docs.astral.sh/uv/)
- PostgreSQL
- Redis

仓库声明的包管理器版本为 `pnpm@9.15.0`。

## 快速开始

### 1. 安装依赖

```bash
git clone <your-repository-url>
cd deep-dig
pnpm install

cd apps/backend
uv sync
cp .env.example .env
uv run alembic upgrade head
cd ../..

cp apps/desktop/.env.example apps/desktop/.env
```

执行迁移前，请确认 PostgreSQL 已启动，并且 `DATABASE_URL` 配置的数据库已经创建。

### 2. 配置后端

编辑 `apps/backend/.env`，至少设置以下配置：

```env
ENV=development
AUTH_SECRET=replace-with-a-long-random-secret
LOCAL_AUTH_USERNAME=admin
LOCAL_AUTH_PASSWORD=replace-with-a-strong-password
```

如果只想在本地验证流程、不调用真实模型，可以使用 fake 模式：

```env
LLM_PROVIDER=fake
```

公开部署时不要使用示例密钥或密码。

### 3. 启动完整本地环境

在仓库根目录执行：

```bash
pnpm dev:start -- --llm fake
```

该命令会启动 Redis、FastAPI API、ARQ Worker 和主 Web UI，但不会启动 PostgreSQL；PostgreSQL
需要提前运行。

主 Web UI 地址：

```text
http://127.0.0.1:5173
```

本地服务地址：

- Web UI：`http://127.0.0.1:5173`
- API：`http://127.0.0.1:8001`
- API 文档：`http://127.0.0.1:8001/docs`
- Redis：`127.0.0.1:6379`

登录时使用后端 `.env` 中配置的 `LOCAL_AUTH_USERNAME` 和 `LOCAL_AUTH_PASSWORD`。

## 开发命令

```bash
# 完整本地环境
pnpm dev:start -- --llm fake

# 使用 apps/backend/.env 中配置的 Provider
pnpm dev:start

# 服务管理
pnpm dev:status
pnpm dev:stop
pnpm dev:restart -- --llm fake
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

| 模式 | 行为 |
| --- | --- |
| `fake` | 返回固定演示结果，不调用外部 API，不产生模型费用 |
| `auto` | 自动使用已配置的可用 Provider |
| `openrouter` | 使用 OpenRouter API |
| `anthropic` | 使用 Anthropic API |
| `openai_compatible` | 使用 OpenAI 兼容的 `/chat/completions` 接口 |

`--llm fake` 只对启动脚本拉起的 API 和 Worker 进程临时生效，不会修改 `.env` 文件。

## 数据与隐私

- 上传的 PDF 字节由后端临时处理，应用工作流不会持久化原始 PDF 文件。
- 解析文本在等待任务执行时可能临时存在 Redis 队列中；任务元数据、提取结果、文件名和哈希
  会根据工作流及用户设置保存。
- 只有启用 `user_settings.store_raw_text` 时才会保存原始解析文本。
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

当前仓库尚未包含许可证文件。如果希望明确他人如何使用、修改和再分发本项目，请在公开发布前
添加 `LICENSE` 文件。
