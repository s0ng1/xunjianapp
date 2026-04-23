# 安全巡检平台第一阶段实现

已包含：

- `backend`：FastAPI 后端接口
- `frontend`：Next.js 结果展示页面
- `db`：PostgreSQL
- `docker-compose.yml`：统一启动本地开发和联调环境
- 第一阶段已落地的功能：
  - 资产管理
  - SSH 连接测试
  - 独立端口扫描
  - Linux 巡检
  - H3C 交换机巡检
  - 基线检查

当前不包含：

- 鉴权与账号体系
- APScheduler 自动调度
- 生产式迁移自动执行流程（受控环境需手动执行迁移命令）

## 目录结构

```text
.
├─ backend
│  ├─ app
│  │  ├─ api
│  │  ├─ core
│  │  ├─ db
│  │  └─ schemas
│  ├─ Dockerfile
│  └─ requirements.txt
├─ frontend
│  ├─ src
│  │  ├─ app
│  │  └─ lib
│  ├─ Dockerfile
│  └─ package.json
├─ .env.example
└─ docker-compose.yml
```

## 运行要求

推荐使用 Docker Desktop，并确保启用了 Docker Compose。

## 启动步骤

1. 复制环境变量文件：

```powershell
Copy-Item .env.example .env
```

2. 构建并启动所有服务：

```powershell
docker compose up --build
```

默认行为说明：

- 根目录 `docker-compose.yml` 默认按开发/联调模式启动
- 默认 `ENVIRONMENT=development`
- 默认 `DB_SCHEMA_INIT_MODE=auto`
- fresh DB 下启动后会自动建表，便于本地直接联调
- 如果你要模拟受控环境，请显式把 `DB_SCHEMA_INIT_MODE` 切到 `migrations`，并在启动前手工执行 Alembic

3. 打开以下地址：

- 前端：[http://localhost:3000](http://localhost:3000)
- 后端健康检查：[http://localhost:8000/health](http://localhost:8000/health)
- 后端就绪检查：[http://localhost:8000/ready](http://localhost:8000/ready)

## 常用命令

启动：

```powershell
docker compose up --build
```

后台启动：

```powershell
docker compose up --build -d
```

停止：

```powershell
docker compose down
```

查看日志：

```powershell
docker compose logs -f
```

只看后端日志：

```powershell
docker compose logs -f backend
```

只看前端日志：

```powershell
docker compose logs -f frontend
```

## 环境变量

根目录 `.env` 支持以下变量：

```env
POSTGRES_DB=sec
POSTGRES_USER=sec_user
POSTGRES_PASSWORD=change_me
POSTGRES_PORT=55432
BACKEND_PORT=8000
FRONTEND_PORT=3000
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
INTERNAL_API_BASE_URL=http://localhost:8000
DB_SCHEMA_INIT_MODE=auto
SSH_CONNECTION_TIMEOUT_SECONDS=10
SSH_COMMAND_READ_TIMEOUT_SECONDS=120
PORT_SCAN_CONNECT_TIMEOUT_SECONDS=1
PORT_SCAN_DEFAULT_PORTS=22,80,443
SSH_TEST_RATE_LIMIT=5/minute
LINUX_INSPECTION_RATE_LIMIT=10/minute
SWITCH_INSPECTION_RATE_LIMIT=10/minute
PORT_SCAN_RATE_LIMIT=20/minute
CREDENTIAL_ENCRYPTION_KEY=local-dev-only-encryption-key
```

说明：

- `DB_SCHEMA_INIT_MODE=auto`：开发环境默认自动建表
- 受控环境建议设置 `DB_SCHEMA_INIT_MODE=migrations`，并先执行 Alembic 迁移
- `POSTGRES_PORT` 默认使用 `55432`，避免与宿主机常见的本地 PostgreSQL `5432` 冲突；容器内部仍然通过 `db:5432` 通信
- `ALLOWED_ORIGINS` 建议同时包含 `localhost` 和 `127.0.0.1`，以及你实际运行前端的端口，例如 `3000` 或 `3001`
- `NEXT_PUBLIC_API_BASE_URL` 给浏览器使用；容器化部署时，前端服务端渲染如需直连后端，可额外设置 `INTERNAL_API_BASE_URL`
- SSH、端口扫描的超时和限流阈值可通过环境变量统一调整
- `PORT_SCAN_DEFAULT_PORTS` 用于指定未显式传参时的默认扫描端口
- `CREDENTIAL_ENCRYPTION_KEY` 用于资产凭据密文存储，受控环境请替换成独立密钥

## 阶段验收

为避免验收依赖宿主机 Python、pytest 或 Node.js 环境，仓库提供了一个固定入口：

```bash
./scripts/phase1_acceptance.sh
```

脚本会完成以下动作：

- `docker compose up -d --build`
- 等待 `db`、`backend`、`frontend` 进入 healthy
- 检查 `/health`、`/ready` 和前端首页
- 在后端容器内执行 SQLite 快测：`pytest -m "not postgres_integration"`
- 在后端容器内执行 PostgreSQL 最小集成测试：`pytest -m postgres_integration`
- 在前端容器内执行 `npm run typecheck`
- 跑一条最小 smoke：创建资产、查询资产、删除资产

如果你已经有自己的 `.env`，脚本会沿用当前配置；如果没有，则使用仓库默认值。

## 数据库迁移

后端已集成 Alembic。

开发环境：

- 默认 `ENVIRONMENT=development` 且 `DB_SCHEMA_INIT_MODE=auto`
- 直接启动应用时会执行 `create_all()` 兜底，便于本地快速运行

受控环境：

- 建议设置 `DB_SCHEMA_INIT_MODE=migrations`
- 建议同时将 `ENVIRONMENT` 设置为 `production`
- 启动应用前先执行：

```bash
alembic -c alembic.ini upgrade head
```

新增迁移：

```bash
alembic -c alembic.ini revision --autogenerate -m "describe change"
```

## 后端说明

后端当前提供：

- `/health`：服务存活检查
- `/ready`：数据库连通性和关键业务表就绪检查
- `POST /api/v1/assets`：新增资产
- `GET /api/v1/assets`：查看资产列表
- `POST /api/v1/assets/{asset_id}/ssh-test`：按资产配置测试 SSH
- `POST /api/v1/assets/{asset_id}/port-scan`：按资产执行端口扫描
- `POST /api/v1/assets/{asset_id}/inspect`：按资产执行巡检
- `POST /api/v1/assets/{asset_id}/baseline`：按资产执行基线检查
- `DELETE /api/v1/assets/{asset_id}`：删除资产
- `POST /api/v1/ssh/test`：测试 SSH 连接
- `POST /api/v1/port-scans/run`：执行独立端口扫描并保存结果
- `GET /api/v1/port-scans`：查看端口扫描结果
- `POST /api/v1/linux-inspections/run`：执行 Linux 巡检并保存结果
- `GET /api/v1/linux-inspections`：查看 Linux 巡检结果
- `POST /api/v1/switch-inspections/h3c/run`：执行 H3C 交换机巡检并返回原始配置
- 统一错误返回结构
- 基础 CORS 配置
- PostgreSQL 连接管理

接口文档：

- Swagger UI：[http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI JSON：[http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

资产新增示例：

```json
{
  "ip": "192.168.1.10",
  "type": "linux",
  "name": "prod-web-01",
  "username": "root",
  "credential_password": "change_me"
}
```

SSH 测试示例：

```json
{
  "ip": "192.168.1.20",
  "username": "root",
  "password": "change_me"
}
```

返回示例：

```json
{
  "success": true,
  "message": "SSH connection succeeded"
}
```

安全约束：

- SSH 测试接口只做即时连接校验，不保存密码
- 服务日志不记录密码字段

Linux 巡检请求示例：

```json
{
  "ip": "192.168.56.10",
  "username": "root",
  "password": "change_me"
}
```

端口扫描请求示例：

```json
{
  "ip": "192.168.56.20",
  "ports": [22, 80, 443]
}
```

端口扫描返回示例：

```json
{
  "id": 1,
  "ip": "192.168.56.20",
  "success": true,
  "message": "Port scan completed: 2 open of 3 checked",
  "checked_ports": [22, 80, 443],
  "open_ports": [
    { "protocol": "tcp", "port": 22, "is_open": true },
    { "protocol": "tcp", "port": 443, "is_open": true }
  ],
  "created_at": "2026-04-10T00:00:00Z"
}
```

Linux 巡检返回示例：

```json
{
  "id": 1,
  "ip": "192.168.56.10",
  "username": "root",
  "success": true,
  "message": "Linux inspection completed",
  "open_ports": {
    "ports": [
      {
        "protocol": "tcp",
        "local_address": "0.0.0.0",
        "port": "22",
        "state": "LISTEN"
      }
    ],
    "raw_output": "tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*"
  },
  "ssh_config": {
    "settings": {
      "port": "22",
      "permitrootlogin": "no"
    },
    "raw_output": "port 22\npermitrootlogin no"
  },
  "firewall_status": {
    "firewalld": "active",
    "ufw": "inactive",
    "iptables_rules": [
      "Chain INPUT (policy ACCEPT)"
    ],
    "raw_output": "__FIREWALLD__\nactive\n__UFW__\ninactive\n__IPTABLES__\nChain INPUT (policy ACCEPT)"
  }
}
```

H3C 交换机巡检请求示例：

```json
{
  "ip": "192.168.10.2",
  "username": "admin",
  "password": "change_me"
}
```

H3C 交换机巡检返回示例：

```json
{
  "success": true,
  "vendor": "H3C",
  "message": "H3C switch inspection completed",
  "raw_config": "sysname CORE-SW-01\ninterface GigabitEthernet1/0/1\n port access vlan 10"
}
```

## 前端说明

前端当前提供：

- 资产总览页：展示资产、最新巡检状态和风险统计
- 资产详情页：展示单台设备的基线结果、开放端口和原始输出
- 告警列表页：基于后端基线失败项聚合未处理告警
- 环境变量驱动的 API 地址配置

## 测试

后端测试需要在 `backend/` 目录执行：

```bash
cd backend
.venv/bin/pytest -q
```

前端构建验证：

```bash
cd frontend
npm run build
```
