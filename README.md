# Nakama 游戏后端接口自动化测试

用 `pytest` + `requests` 对本地部署的开源游戏后端 **Nakama** 做接口自动化测试，覆盖认证、账号、排行榜、存储四类接口，用例分三层：**功能（L1）/ 异常与鉴权（L2）/ 并发一致性（L3）**。

## 被测系统

[Nakama](https://heroiclabs.com/nakama/)（heroiclabs/nakama）—— 开源游戏后端服务端。本项目只测它的 **HTTP 接口**（REST，默认 `http://127.0.0.1:7350`），不涉及任何客户端 / 界面。

## 技术栈

- Python 3.14 + `pytest` 9.1.1 + `requests` + `allure-pytest`
- Docker / Docker Compose：Nakama + PostgreSQL 16
- 服务端用 Lua 模块（`modules/init.lua`）在启动时初始化测试排行榜

## 目录结构

```
docker-compose.yml     # Nakama + PostgreSQL 环境
modules/init.lua       # 启动时创建测试排行榜 test_leaderboard
config/config.py       # BASE_URL / SERVER_KEY / LEADERBOARD_ID
utils/client.py        # NakamaClient —— 接口薄封装（一个方法 = 一个接口）
conftest.py            # fixture：client / new_device_id / authed_client
tests/                 # 测试用例
```

## 快速开始

```bash
# 1. 起被测服务
docker compose up -d

# 2. 装依赖
pip install -r requirements.txt

# 3. 跑测试
pytest
```

生成 Allure 报告：

```bash
python -m pytest --alluredir=report/allure-results
allure generate report/allure-results -o report/allure-report --clean
# 打开 report/allure-report/index.html
```

## 测试范围

**L1 功能**：正常路径的返回是否正确

- `test_auth.py`：新设备首次登录建号、同设备复用账号、错误 server key 被拒
- `test_account.py`：读取账号、修改昵称、超长昵称被拒
- `test_leaderboard.py`：提交分数返回记录、列表含已提交分数、榜单降序排列
- `test_storage.py`：写入并读回存储对象、读不存在的对象返回空

**L2 异常与鉴权**：错误输入 / 越权

- `test_errors.py`：无 token 返回 401、坏 token 返回 401、缺必填字段的行为
- `test_storage.py`：他人无法读取 owner-only（`permission_read=1`）的存储对象

**L3 并发一致性**

- `test_concurrency.py`：20 个玩家并发提交分数，验证无丢失且榜单有序

合计 **18 条用例**。

## 观察到的边界行为（实测，非编造）

测试过程中通过手动探测（curl / Postman）记录了以下真实行为：

1. **超长昵称返回 500（疑似缺陷）**：`display_name` 上限为 255 字符，超过时服务器返回 `500`。用户输入超长属于客户端错误，规范做法应返回 `4xx`，返回 `500` 说明服务端未对该输入做校验处理。
2. **缺失必填字段被静默接受**：提交排行榜分数不带 `score` 字段时，服务器不报错，按 0 分建了记录；写入存储不带 `objects` 字段时返回 200 空操作。属于较为宽松的校验行为，已按实际行为固化进断言。

以上为在本地部署版本上观察到的行为，是否为设计意图需结合版本确认。

## 说明

本项目用于学习与求职作品展示。测试用例的真实契约（如 `score` 为字符串、`created` 为 false 时字段被省略、存储读取需带 `user_id` 等）均在探测后按实际行为编写。
