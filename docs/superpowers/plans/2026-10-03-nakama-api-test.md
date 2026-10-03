# Nakama 游戏后端接口自动化测试 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 pytest + requests 对本地 Docker 运行的 Nakama 游戏后端做接口自动化测试，产出可推 GitHub 的个人作品仓库。

**Architecture:** `docker compose` 拉起 Nakama + CockroachDB；一个 Lua 模块在服务启动时创建测试排行榜；Python 侧用一层薄客户端封装 Nakama 的 REST 调用，`conftest.py` 提供"已完成设备登录"的 fixture；测试按接口域分文件，分 L1 功能 / L2 异常鉴权 / L3 并发三层。

**Tech Stack:** Python 3.10+、pytest、requests、allure-pytest、Docker Desktop、Nakama、CockroachDB。

**Spec:** `docs/superpowers/specs/2026-10-03-nakama-api-test-design.md`

## Global Constraints

- 被测地址固定：`http://127.0.0.1:7350`；HTTP server key 默认 `defaultkey`（均可用环境变量覆盖）。
- 认证方式（全项目统一）：
  - authenticate 类接口：`Authorization: Basic base64(server_key + ":")`
  - 其余接口：`Authorization: Bearer <session_token>`
- 排行榜**必须服务端预创建**（Nakama 客户端 API 没有建榜接口），由 `modules/init.lua` 在启动时创建，id = `test_leaderboard`。
- **不编造缺陷**：没有真实缺陷就如实报"全覆盖、未发现缺陷"。
- **用例由用户亲手写/改**，Claude 给结构、完整示例供其评审，不代写整套后让用户"看不懂"。

## Review Focus

以下是 spec 隐含、但单靠 happy-path 用例不会覆盖、最容易在真实使用中咬人的输入/情形。每条都在对应任务的测试里钉住：

1. **设备 id 复用**：同一 device id 二次登录应返回已存在账号（`created=false`），不应新建或报错。
2. **无 / 错误 token**：缺失或伪造的 Bearer token 必须 401，不能放行。
3. **越权读**：A 用户的 Owner-Read 存储对象，B 用户读不到（返回空，而非报错或泄露）。
4. **并发提交**：多用户并发写分后，榜单必须包含全部记录且排序正确（不能丢写、乱序）。
5. **缺必填字段**：写排行榜记录缺 `score` / 写存储缺 `objects` 时返回 4xx（不能 500）。

---

### Task 1: 搭建并跑通 Nakama 环境

**Files:**
- Create: `docker-compose.yml`
- Create: `modules/init.lua`
- Create: `.gitignore`

**Interfaces:**
- Produces: 一个运行中的 Nakama（`http://127.0.0.1:7350`，key `defaultkey`）和一个已创建的排行榜 `test_leaderboard`（供 Task 5/6 使用）。

- [ ] **Step 1: 用户安装 Docker Desktop（Claude 给指引，用户操作）**

  下载 Docker Desktop for Windows → 安装 → 启动 → 确认底部状态为 "Engine running"。
  验证命令：
  ```bash
  docker --version && docker compose version
  ```
  Expected: 两条都打印版本号。
  若安装受阻（WSL2 不可用等），停止并回到 spec 第 9 节回退方案。

- [ ] **Step 2: 写 `docker-compose.yml`**

  ```yaml
  services:
    cockroachdb:
      image: cockroachdb/cockroach:latest
      command: start-single-node --insecure --store=attrs=ssd,path=/var/lib/cockroach/
      restart: "no"
      volumes:
        - data:/var/lib/cockroach
      ports:
        - "26257:26257"
        - "8080:8080"
    nakama:
      image: heroiclabs/nakama:latest
      entrypoint:
        - "/bin/sh"
        - "-ecx"
        - >
          /nakama/nakama migrate up --database.address root@cockroachdb:26257 &&
          exec /nakama/nakama --name nakama1 --database.address root@cockroachdb:26257
          --logger.level DEBUG --session.token_expiry_sec 7200
      restart: "no"
      depends_on:
        - cockroachdb
      volumes:
        - ./modules:/nakama/data/modules
      ports:
        - "7349:7349"
        - "7350:7350"
        - "7351:7351"
      healthcheck:
        test: ["CMD", "/nakama/nakama", "healthcheck"]
        interval: 10s
        timeout: 5s
        retries: 5
  volumes:
    data:
  ```

  说明：`./modules:/nakama/data/modules` 让 Nakama 从项目里的 `modules/` 加载 Lua 扩展。

- [ ] **Step 3: 写 `modules/init.lua`（启动时创建测试排行榜）**

  ```lua
  local nk = require("nakama")

  local function InitModule(context, payload)
      nk.logger_info("InitModule: creating test_leaderboard")
      nk.leaderboard_create("test_leaderboard", false, "desc", "best", "", {})
      return nil
  end
  ```

  说明：`authoritative=false` 表示允许客户端直接写分（便于测试）；`"desc"` 降序；`"best"` 表示同一用户保留最高分。

- [ ] **Step 4: 写 `.gitignore`**

  ```gitignore
  __pycache__/
  .pytest_cache/
  venv/
  report/
  *.pyc
  ```

- [ ] **Step 5: 起服务并确认健康**

  ```bash
  docker compose up -d
  docker compose ps
  ```
  Expected: `cockroachdb` 与 `nakama` 均为 running/healthy。

- [ ] **Step 6: 验证排行榜已创建（本任务的"测试"）**

  用默认 key 做设备登录拿 token，再列出榜单：
  ```bash
  TOKEN=$(curl -s -X POST "http://127.0.0.1:7350/v2/account/authenticate/device?create=true" \
    -H "Authorization: Basic $(printf 'defaultkey:' | base64)" \
    -H "Content-Type: application/json" -d '{"id":"probe-001"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
  curl -s "http://127.0.0.1:7350/v2/leaderboard/test_leaderboard" -H "Authorization: Bearer $TOKEN"
  ```
  Expected: 返回 JSON（records 为空数组即可），**不是** 404/400。
  若报错，看 `docker compose logs nakama | grep -i leaderboard` 排查 `init.lua`：
  - 若日志提示 `leaderboard_create` 参数错误 → 该版本 Lua 签名与上面不同，用控制台 `http://127.0.0.1:7351` 的 API Explorer 核对后调整参数顺序/个数。
  - 若模块没被加载 → 确认 `modules/` 已挂载且文件名为 `.lua`。

- [ ] **Step 7: Commit**

  ```bash
  git add docker-compose.yml modules/init.lua .gitignore
  git commit -m "chore: 搭建 Nakama+CockroachDB 环境与测试排行榜初始化模块"
  ```

---

### Task 2: 测试骨架与登录 fixture

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `config/config.py`
- Create: `utils/client.py`
- Create: `conftest.py`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Produces（后续任务依赖，名称必须一致）：
  - `config.config`: `BASE_URL`、`SERVER_KEY`、`LEADERBOARD_ID`
  - `utils.client.NakamaClient(base_url, server_key)`，方法：
    - `authenticate_device(device_id, create=True, username=None) -> requests.Response`
    - `session(device_id) -> str`（登录并保存 token）
    - `bearer -> dict`（属性，返回 Bearer 头）
    - `get_account() / update_account(display_name) -> requests.Response`
    - `write_leaderboard_record(leaderboard_id, score, subscore=None, metadata=None) -> requests.Response`
    - `list_leaderboard_records(leaderboard_id, limit=None, owner_ids=None) -> requests.Response`
    - `write_storage(objects) / read_storage(object_ids) -> requests.Response`
  - `conftest` fixtures: `client`、`new_device_id`、`authed_client`

- [ ] **Step 1: 写 `requirements.txt`**

  ```
  pytest
  requests
  allure-pytest
  ```

- [ ] **Step 2: 写 `pytest.ini`**

  ```ini
  [pytest]
  testpaths = tests
  addopts = -v
  ```

- [ ] **Step 3: 写 `config/config.py`**

  ```python
  import os

  BASE_URL = os.getenv("NAKAMA_BASE_URL", "http://127.0.0.1:7350")
  SERVER_KEY = os.getenv("NAKAMA_SERVER_KEY", "defaultkey")
  LEADERBOARD_ID = "test_leaderboard"
  ```

- [ ] **Step 4: 写失败冒烟测试 `tests/test_smoke.py`**

  ```python
  from utils.client import NakamaClient
  from config.config import BASE_URL, SERVER_KEY


  def test_authenticate_device_returns_token(new_device_id):
      client = NakamaClient(BASE_URL, SERVER_KEY)
      resp = client.authenticate_device(new_device_id)
      assert resp.status_code == 200
      assert resp.json().get("token")
  ```

- [ ] **Step 5: 运行确认失败**

  ```bash
  python -m pytest tests/test_smoke.py -v
  ```
  Expected: FAIL，报 `ModuleNotFoundError: No module named 'utils.client'`（或 fixture `new_device_id` not found）。

- [ ] **Step 6: 写 `utils/client.py`**

  ```python
  import base64

  import requests


  class NakamaClient:
      def __init__(self, base_url, server_key):
          self.base_url = base_url.rstrip("/")
          self.server_key = server_key
          self.token = None

      def _basic_auth(self):
          raw = f"{self.server_key}:".encode()
          return {"Authorization": "Basic " + base64.b64encode(raw).decode()}

      @property
      def bearer(self):
          return {"Authorization": f"Bearer {self.token}"}

      def authenticate_device(self, device_id, create=True, username=None):
          params = {"create": str(create).lower()}
          if username:
              params["username"] = username
          return requests.post(
              f"{self.base_url}/v2/account/authenticate/device",
              params=params,
              json={"id": device_id},
              headers=self._basic_auth(),
          )

      def session(self, device_id):
          resp = self.authenticate_device(device_id)
          resp.raise_for_status()
          self.token = resp.json()["token"]
          return self.token

      def get_account(self):
          return requests.get(f"{self.base_url}/v2/account", headers=self.bearer)

      def update_account(self, display_name):
          return requests.put(
              f"{self.base_url}/v2/account",
              json={"display_name": display_name},
              headers=self.bearer,
          )

      def write_leaderboard_record(self, leaderboard_id, score, subscore=None, metadata=None):
          body = {"score": score}
          if subscore is not None:
              body["subscore"] = subscore
          if metadata is not None:
              body["metadata"] = metadata
          return requests.post(
              f"{self.base_url}/v2/leaderboard/{leaderboard_id}",
              json=body,
              headers=self.bearer,
          )

      def list_leaderboard_records(self, leaderboard_id, limit=None, owner_ids=None):
          params = {}
          if limit is not None:
              params["limit"] = limit
          if owner_ids is not None:
              params["owner_ids"] = owner_ids
          return requests.get(
              f"{self.base_url}/v2/leaderboard/{leaderboard_id}",
              params=params,
              headers=self.bearer,
          )

      def write_storage(self, objects):
          return requests.put(
              f"{self.base_url}/v2/storage", json={"objects": objects}, headers=self.bearer
          )

      def read_storage(self, object_ids):
          return requests.post(
              f"{self.base_url}/v2/storage", json={"object_ids": object_ids}, headers=self.bearer
          )
  ```

- [ ] **Step 7: 写 `conftest.py`**

  ```python
  import uuid

  import pytest

  from config.config import BASE_URL, SERVER_KEY
  from utils.client import NakamaClient


  @pytest.fixture
  def client():
      return NakamaClient(BASE_URL, SERVER_KEY)


  @pytest.fixture
  def new_device_id():
      return f"test-{uuid.uuid4()}"


  @pytest.fixture
  def authed_client(client, new_device_id):
      client.session(new_device_id)
      return client
  ```

- [ ] **Step 8: 运行确认通过**

  ```bash
  python -m pytest tests/test_smoke.py -v
  ```
  Expected: PASS（1 passed）。

- [ ] **Step 9: Commit**

  ```bash
  git add requirements.txt pytest.ini config/ utils/ conftest.py tests/test_smoke.py
  git commit -m "feat: 测试骨架、NakamaClient 薄封装与登录 fixture"
  ```

---

### Task 3: 认证测试（L1）

**Files:**
- Create: `tests/test_auth.py`

**Interfaces:**
- Consumes: `NakamaClient`、`client`、`new_device_id` fixtures

- [ ] **Step 1: 写失败测试 `tests/test_auth.py`**

  ```python
  from config.config import BASE_URL
  from utils.client import NakamaClient


  def test_authenticate_device_creates_account(client, new_device_id):
      resp = client.authenticate_device(new_device_id, create=True)
      assert resp.status_code == 200
      body = resp.json()
      assert body["token"]
      assert "refresh_token" in body
      assert body.get("created") is True


  def test_same_device_id_reuses_account(client, new_device_id):
      client.authenticate_device(new_device_id, create=True)
      second = client.authenticate_device(new_device_id, create=True)
      assert second.status_code == 200
      assert second.json().get("created") is False


  def test_authenticate_with_wrong_server_key_fails(new_device_id):
      bad = NakamaClient(BASE_URL, "definitely-wrong-key")
      resp = bad.authenticate_device(new_device_id)
      assert resp.status_code in (401, 403)
  ```

- [ ] **Step 2: 运行确认现状**

  ```bash
  python -m pytest tests/test_auth.py -v
  ```
  Expected: 因 client 方法已存在，多数可能直接通过。若某条关于 `created` 字段的断言失败 → 说明该字段名/语义与假设不同，去控制台 API Explorer 核对响应 schema 后修正断言（**改断言贴合真实契约，不要改被测系统**）。

- [ ] **Step 3: 全部通过后 Commit**

  ```bash
  git add tests/test_auth.py
  git commit -m "test: 补充认证接口用例（复用 device id / 错误 key）"
  ```

---

### Task 4: 账号接口测试（L1）

**Files:**
- Create: `tests/test_account.py`

**Interfaces:**
- Consumes: `authed_client` fixture、`NakamaClient.get_account/update_account`

- [ ] **Step 1: 写失败测试 `tests/test_account.py`**

  ```python
  def test_get_account_returns_user(authed_client):
      resp = authed_client.get_account()
      assert resp.status_code == 200
      assert "user" in resp.json()


  def test_update_display_name(authed_client):
      resp = authed_client.update_account("testplayer")
      assert resp.status_code == 200
      assert resp.json()["display_name"] == "testplayer"


  def test_update_display_name_too_long_rejected(authed_client):
      resp = authed_client.update_account("x" * 200)
      assert 400 <= resp.status_code < 500
  ```

- [ ] **Step 2: 运行**

  ```bash
  python -m pytest tests/test_account.py -v
  ```
  Expected: PASS。若昵称长度上限与假设不符（Nakama 上限为 128 字符），调整测试数据使其确实超限。

- [ ] **Step 3: Commit**

  ```bash
  git add tests/test_account.py
  git commit -m "test: 补充账号读取与昵称更新用例"
  ```

---

### Task 5: 排行榜接口测试（L1）

**Files:**
- Create: `tests/test_leaderboard.py`

**Interfaces:**
- Consumes: `authed_client`、`client`、`LEADERBOARD_ID`、`NakamaClient.write_leaderboard_record/list_leaderboard_records`
- 依赖 Task 1 的 `test_leaderboard` 已存在

- [ ] **Step 1: 写失败测试 `tests/test_leaderboard.py`**

  ```python
  import uuid

  from config.config import BASE_URL, SERVER_KEY, LEADERBOARD_ID
  from utils.client import NakamaClient


  def test_write_score_returns_record(authed_client):
      resp = authed_client.write_leaderboard_record(LEADERBOARD_ID, score=100)
      assert resp.status_code == 200
      assert resp.json()["score"] == 100


  def test_list_contains_submitted_score(authed_client):
      authed_client.write_leaderboard_record(LEADERBOARD_ID, score=250)
      resp = authed_client.list_leaderboard_records(LEADERBOARD_ID, limit=100)
      assert resp.status_code == 200
      scores = [r["score"] for r in resp.json().get("records", [])]
      assert 250 in scores


  def test_leaderboard_sorted_descending():
      players = []
      for s in (10, 300, 150):
          c = NakamaClient(BASE_URL, SERVER_KEY)
          c.session(f"lb-{uuid.uuid4()}")
          c.write_leaderboard_record(LEADERBOARD_ID, score=s)
          players.append(c)
      resp = players[0].list_leaderboard_records(LEADERBOARD_ID, limit=100)
      scores = [r["score"] for r in resp.json().get("records", [])]
      assert scores == sorted(scores, reverse=True)
  ```

- [ ] **Step 2: 运行**

  ```bash
  python -m pytest tests/test_leaderboard.py -v
  ```
  Expected: PASS。若返回 404 → 榜单没建成，回 Task 1 Step 6 排查 `init.lua`。

- [ ] **Step 3: Commit**

  ```bash
  git add tests/test_leaderboard.py
  git commit -m "test: 补充排行榜提交与列表用例（含降序校验）"
  ```

---

### Task 6: 存储接口测试（L1）

**Files:**
- Create: `tests/test_storage.py`

**Interfaces:**
- Consumes: `authed_client`、`NakamaClient.write_storage/read_storage`

- [ ] **Step 1: 写失败测试 `tests/test_storage.py`**

  ```python
  import json


  def test_write_and_read_storage_object(authed_client):
      value = json.dumps({"progress": 50})
      w = authed_client.write_storage(
          [{"collection": "saves", "key": "save1", "value": value}]
      )
      assert w.status_code == 200
      assert w.json()["acks"][0]["version"]

      r = authed_client.read_storage([{"collection": "saves", "key": "save1"}])
      assert r.status_code == 200
      objects = r.json().get("objects", [])
      assert len(objects) == 1
      assert json.loads(objects[0]["value"])["progress"] == 50


  def test_read_missing_object_returns_empty(authed_client):
      r = authed_client.read_storage([{"collection": "saves", "key": "nope"}])
      assert r.status_code == 200
      assert r.json().get("objects", []) == []
  ```

- [ ] **Step 2: 运行**

  ```bash
  python -m pytest tests/test_storage.py -v
  ```
  Expected: PASS。若读取返回的对象里 `value` 需二次解析，说明存的是字符串——符合预期。

- [ ] **Step 3: Commit**

  ```bash
  git add tests/test_storage.py
  git commit -m "test: 补充存储对象写入/读取与缺失返回空用例"
  ```

---

### Task 7: 异常与鉴权测试（L2）

**Files:**
- Create: `tests/test_errors.py`

**Interfaces:**
- Consumes: `authed_client`、`NakamaClient`

- [ ] **Step 1: 写失败测试 `tests/test_errors.py`**

  ```python
  import requests

  from config.config import BASE_URL, LEADERBOARD_ID


  def test_missing_token_rejected():
      resp = requests.get(f"{BASE_URL}/v2/account")
      assert resp.status_code == 401


  def test_malformed_token_rejected():
      resp = requests.get(
          f"{BASE_URL}/v2/account",
          headers={"Authorization": "Bearer not-a-real-token"},
      )
      assert resp.status_code == 401


  def test_write_score_without_score_field_rejected(authed_client):
      resp = requests.post(
          f"{BASE_URL}/v2/leaderboard/{LEADERBOARD_ID}",
          json={},
          headers=authed_client.bearer,
      )
      assert 400 <= resp.status_code < 500


  def test_write_storage_without_objects_field_rejected(authed_client):
      resp = requests.put(
          f"{BASE_URL}/v2/storage", json={}, headers=authed_client.bearer
      )
      assert 400 <= resp.status_code < 500
  ```

- [ ] **Step 2: 运行**

  ```bash
  python -m pytest tests/test_errors.py -v
  ```
  Expected: PASS。若缺字段返回的是 200（被容错）或 500（未处理），**如实记录实际行为**——若为 500，这是一个可写进缺陷单的真实问题。

- [ ] **Step 3: Commit**

  ```bash
  git add tests/test_errors.py
  git commit -m "test: 补充无/坏 token 与缺必填字段的异常用例"
  ```

---

### Task 8: 存储越权读测试（L2）

**Files:**
- Modify: `tests/test_storage.py`（追加用例）

**Interfaces:**
- Consumes: `client`、`new_device_id`、`NakamaClient`

- [ ] **Step 1: 追加失败测试到 `tests/test_storage.py`**

  ```python
  import uuid

  from config.config import BASE_URL, SERVER_KEY
  from utils.client import NakamaClient


  def test_other_user_cannot_read_owner_only_object(new_device_id):
      owner = NakamaClient(BASE_URL, SERVER_KEY)
      owner.session(new_device_id)
      owner.write_storage(
          [{"collection": "saves", "key": "private1", "value": "{}",
            "permission_read": 1, "permission_write": 1}]
      )
      owner_id = owner.get_account().json()["user"]["id"]

      intruder = NakamaClient(BASE_URL, SERVER_KEY)
      intruder.session(f"intruder-{uuid.uuid4()}")
      resp = intruder.read_storage(
          [{"collection": "saves", "key": "private1", "user_id": owner_id}]
      )
      assert resp.status_code == 200
      assert resp.json().get("objects", []) == []
  ```

- [ ] **Step 2: 运行**

  ```bash
  python -m pytest tests/test_storage.py -v
  ```
  Expected: PASS（他人读不到 = 空）。若返回了对象，是**真实越权缺陷**，写进缺陷单。

- [ ] **Step 3: Commit**

  ```bash
  git add tests/test_storage.py
  git commit -m "test: 补充存储越权读用例（Owner-Read 对象他人不可见）"
  ```

---

### Task 9: 并发一致性测试（L3，重点卖点）

**Files:**
- Create: `tests/test_concurrency.py`

**Interfaces:**
- Consumes: `NakamaClient`、`BASE_URL`、`SERVER_KEY`、`LEADERBOARD_ID`

- [ ] **Step 1: 写失败测试 `tests/test_concurrency.py`**

  ```python
  import uuid
  from concurrent.futures import ThreadPoolExecutor

  from config.config import BASE_URL, SERVER_KEY, LEADERBOARD_ID
  from utils.client import NakamaClient


  def _submit_score(score):
      c = NakamaClient(BASE_URL, SERVER_KEY)
      c.session(f"concurrent-{uuid.uuid4()}")
      return c.write_leaderboard_record(LEADERBOARD_ID, score=score).status_code


  def test_concurrent_writes_all_persist_and_sorted():
      scores = list(range(1000, 1000 + 20))
      with ThreadPoolExecutor(max_workers=10) as pool:
          statuses = list(pool.map(_submit_score, scores))
      assert all(s == 200 for s in statuses)

      c = NakamaClient(BASE_URL, SERVER_KEY)
      c.session(f"reader-{uuid.uuid4()}")
      resp = c.list_leaderboard_records(LEADERBOARD_ID, limit=100)
      records = resp.json().get("records", [])
      got = [r["score"] for r in records]
      assert all(s in got for s in scores), "并发写入有丢失"
      assert got == sorted(got, reverse=True), "榜单未按降序排列"
  ```

- [ ] **Step 2: 运行（多次）**

  ```bash
  python -m pytest tests/test_concurrency.py -v
  ```
  连跑 3 次。Expected: PASS。
  若有记录丢失或乱序 → 是**真实一致性缺陷**，记录复现条件并写进缺陷单。

- [ ] **Step 3: Commit**

  ```bash
  git add tests/test_concurrency.py
  git commit -m "test: 补充排行榜并发写入一致性用例"
  ```

---

### Task 10: 报告、README 与推送

**Files:**
- Create: `README.md`
- Create: `run.py`（可选，一键跑测试 + 生成 allure 报告）

**Interfaces:**
- Consumes: 全套测试

- [ ] **Step 1: 生成测试报告**

  ```bash
  python -m pytest --alluredir=report/allure-results
  ```
  Expected: 全部用例通过，`report/allure-results/` 生成 JSON。
  （Allure CLI 用户已装在 `E:\allure-2.46.0\bin\allure`，可 `allure generate` 出 HTML。）

- [ ] **Step 2: 写 `README.md`（Diátaxis：简介/技术栈/快速开始/测试范围/运行方式）**

  必须包含：项目简介、被测系统（Nakama）、技术栈、`docker compose up -d` 起环境、`pytest` 跑测试、测试范围（L1/L2/L3）。**不写"发现 N 个 bug"除非真发现。**

- [ ] **Step 3: 记录实际数字（回填简历与 README）**

  统计真实用例条数、通过数、并发用例表现，填入 spec 第 10 节简历模板的空位。

- [ ] **Step 4: 提交并推 GitHub**

  ```bash
  git add README.md run.py
  git commit -m "docs: 补充 README 与运行说明"
  gh repo create nakama-api-test --public --source=. --push
  ```
  Expected: 仓库出现在 GitHub 账号 `mohao111` 下。

---

## Self-Review 记录

- **Spec 覆盖**：L1（Task 3/4/5/6）、L2（Task 7/8）、L3（Task 9）、环境（Task 1）、框架（Task 2）、产出物（Task 10）均已落任务。spec 第 6 节的"可选弱网 Clumsy"未单列任务——可作 Task 9 的可选延伸，不阻塞主线。
- **占位符扫描**：无 TBD/TODO；仅 Task 1 的 image 用 `latest`（因本机无网络无法核对版本号），并在执行中以 healthcheck 验证。
- **类型一致性**：`NakamaClient` 方法名与各测试调用一致；fixture 名 `client/new_device_id/authed_client` 全局一致。
- **Review Focus**：5 条均已在对应任务钉测试（#1→Task3、#2→Task7、#3→Task8、#4→Task9、#5→Task7）。
