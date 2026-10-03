# Nakama 游戏后端接口自动化测试 — 设计文档

日期：2026-10-03
状态：待用户复核

## 1. 背景与目标

应届生秋招测开/游戏测试方向的**个人作品项目**。用一个真实、可控的开源游戏后端（Nakama），
实践并展示**接口自动化测试**能力。

目标（成功标准）：

1. 能用 `docker compose` 在本地拉起 Nakama（含其数据库），并通过 REST 接口访问。
2. 有一套用 pytest + requests 写的、**自己能逐句讲清**的接口自动化测试套件。
3. 覆盖认证/账号/排行榜/存储四类接口，含功能、异常鉴权、并发一致性三类测试。
4. 产出可推 GitHub 的仓库：测试代码 + README + 测试报告 +（若有）缺陷单。
5. 面试时能从"为什么用接口测试""覆盖了什么""发现了什么"讲清楚。

## 2. 非目标（明确不做）

- 不做 UI/客户端自动化（本轮聚焦接口层）。
- 不测**游戏客户端**表现（客户端弱网、兼容性属于另一条线，不在本项目范围）。
- 不修改 Nakama 源码；被测对象是**现成的官方镜像**。
- **不编造缺陷**。没有真实缺陷就如实报"全覆盖、未发现缺陷"，用覆盖率与边界验证作为作品价值。

## 3. 被测系统

- **Nakama**：开源游戏后端（Heroic Labs），提供 REST + gRPC API。
  - 本地地址：`http://127.0.0.1:7350`（HTTP API 端口）
  - 控制台：`http://127.0.0.1:7351`
  - server key（HTTP key）：默认 `defaultkey`
- **数据库**：CockroachDB（Nakama 依赖），由 compose 一并拉起。
- 运行方式：项目根目录 `docker-compose.yml`，`docker compose up -d`。
- 自建自控 → 可自由做并发/边界/弱网实验。

## 4. 环境前置

- 安装 **Docker Desktop**（Windows，依赖 WSL2）。用户手动安装，Claude 负责逐步指引。
- 已具备：系统 Python 3.10+（支持 pytest）、git、GitHub 账号 `mohao111`。
- Docker 镜像与 WSL2 默认占 C 盘；本项目代码放 E 盘以减轻 C 盘压力。

## 5. 测试框架设计

**形态：纯 pytest + requests + fixture（不使用 Excel 数据驱动）。**

理由：游戏接口的每个用例通常要携带动态 token、运行期新生成的 leaderboard id 等，
数据表更笨重；纯代码更直白，面试更易讲解。

分层（参照用户既有习惯）：

- `config/`：配置（BASE_URL、SERVER_KEY 等，敏感项走环境变量）
- `conftest.py`：fixture（未认证 session、已完成设备登录并带 Bearer token 的 session、
  测试数据构造与清理），明确 fixture 的 scope 与 yield 语义
- `utils/`：若需要的公共辅助（如统一请求封装、响应 schema 断言）
- `tests/`：按接口域分文件，用例直接写在 `.py` 中

复用用户已掌握的：pytest、requests、fixture 生命周期、allure 报告。

## 6. 测试范围

按三层递进：

**L1 功能**
- 认证：设备登录 → 获取 session token
- 账号：读取账号信息、更新昵称（含字段校验）
- 排行榜：创建排行榜 → 提交分数 → 查询榜单（排序、分页）
- 存储：写入/读取存储对象

**L2 异常与鉴权**
- 无效/过期 token → 401
- 缺失必填参数 → 400
- 资源不存在 → 404
- 字段类型/取值非法 → 4xx
- 越权访问（以 A 的凭据操作 B 的资源）

**L3 一致性与并发（本项目的重点卖点）**
- 同一玩家重复提交分数：行为是否符合预期（覆盖 vs 累加）
- 多玩家并发提交后，榜单顺序是否一致、有无丢失
- （可选）用 Clumsy 在**测试机 ↔ Nakama 之间**限速/丢包，观察接口重试与幂等
  （注意：这是**接口层**弱网，非客户端弱网；客户端弱网不在本项目范围，见第 2 节）

## 7. 目录结构（规划）

```
nakama-api-test/
├─ docker-compose.yml         # Nakama + CockroachDB
├─ requirements.txt
├─ pytest.ini
├─ config/
│  └─ config.py               # BASE_URL / SERVER_KEY
├─ conftest.py                # fixtures
├─ utils/                     # 公共辅助（按需）
├─ tests/
│  ├─ test_auth.py
│  ├─ test_account.py
│  ├─ test_leaderboard.py
│  └─ test_storage.py
├─ report/                    # allure 结果（gitignore）
├─ README.md
└─ docs/superpowers/specs/    # 本设计文档
```

## 8. 产出物

1. pytest 测试套件（推 GitHub，独立仓库）
2. `README.md`（Diátaxis 结构：简介/技术栈/快速开始/测试范围/运行方式）
3. allure 测试报告
4. 若有真实缺陷 → 缺陷单（标题/环境/复现/证据/影响/建议）

## 9. 风险与回退

- **Docker Desktop 装不上 / WSL2 不可用** → 回退方案 1（Nakama + CockroachDB 二进制手动装）
  或方案 3（改测公开游戏 API，如 Riot/Steam/OpenDota）。
- **L1/L2 大概率全绿**（Nakama 成熟）→ 这不是失败；价值在覆盖率与边界/并发验证。
  真正的缺陷机会在 L3，且不保证出现，如实报告。
- **讲不清的风险** → 用例由用户在主循环中亲手写/改，Claude 只给结构与示例供评审，
  不代写整套后让用户"看不懂"。

## 10. 简历定位（数字以实测为准，实测后回填）

> 基于 Docker 搭建 **Nakama 开源游戏后端**环境，用 pytest + requests 对其
> **认证 / 账号 / 排行榜 / 存储** 接口做自动化测试，覆盖 __ 条用例，
> 重点验证**并发一致性与异常处理**，发现 __ 项问题。
