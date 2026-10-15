# 芝春情感陪伴数字人 · 初赛 Demo

多智能体情感陪伴 Demo，跑通
「用户输入 → 情感识别 → MBTI 路由 → 记忆检索 → 回复生成 → 情绪驱动(TTS/渲染 Mock)」完整链路。

> 零外部大模型 / 零 embedding / 零真实 TTS 依赖，`pip install` 即可跑通。
> 详细设计见《初赛行动规划书.md》与《分工前置.md》。

## 技术栈

- Python 3.10+
- FastAPI + Uvicorn
- Pydantic v2
- pytest

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
uvicorn app.main:app --reload

# 3. 健康检查
curl http://127.0.0.1:8000/health
```

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/chat` | 对话（`session_id` 留空由服务端生成 uuid4，续接时回传） |
| PUT | `/mbti` | 手动覆盖 MBTI（立即生效，清空窗口/计数） |
| POST | `/session/{id}/end` | 显式结束会话（不存在返回 404） |
| GET | `/session/stats` | 当前活跃会话数 |

### 对话请求示例

```json
POST /chat
{
  "session_id": "",
  "text": "我今天很开心"
}
```

首次返回的 `session_id` 是服务端生成的 uuid4（不可枚举），后续对话回传该 id 以续接同一会话。

## 运行测试

```bash
python -m pytest tests/ -q
```

覆盖：情感识别、MBTI 切片路由、三层记忆、安全风控、Mock LLM、会话管理、并发隔离、端到端链路。

## 命令行 Demo

```bash
python -m demo              # 交互式多轮对话
python -m demo --scripted   # 内置剧本自动演示（含 MBTI 覆盖 + 安全拦截）
```

## 目录结构

```
app/
├── main.py                 # FastAPI 入口 + 路由
├── config.py               # 公共配置
├── schemas.py              # Pydantic 数据模型
├── llm/                    # LLM 接入区（换真模型只改这里）
│   ├── base.py             # LLMClient 抽象基类
│   ├── mock.py             # MockLLM（初赛默认）
│   ├── qwen.py             # QwenLLM 占位
│   └── factory.py          # get_llm() 工厂
├── agents/
│   ├── router_agent.py     # 主调度编排
│   ├── memory_agent.py     # 记忆检索/组装
│   └── personality_agent.py# 加载 Prompt + 调 LLM
├── modules/
│   ├── emotion.py          # 情感识别（规则+兜底）
│   ├── session.py          # Session + SessionManager
│   ├── mbti_router.py      # 切片/窗口/投票
│   ├── memory_store.py     # 三层记忆存储
│   ├── safety.py           # 安全风控
│   ├── tts.py              # Mock TTS
│   └── avatar.py           # Mock 渲染
└── prompts/
    └── mbti_prompts.py     # 16 种 MBTI + 通用兜底 Prompt
```

## 接入真实 LLM（决赛）

只改 `app/llm/` 接入区三处，业务 Agent 零改动：

1. 填充 `app/llm/qwen.py` 的 `generate` / `infer_mbti` / `classify_emotion` 三个方法（真实 HTTP 调用）；
2. `app/llm/factory.py` 注册 `"qwen"` 分支；
3. 设置环境变量：

```bash
export LLM_BACKEND=qwen
export LLM_API_KEY=...
export LLM_BASE_URL=...
export LLM_MODEL_NAME=qwen2.5-7b-instruct
```

## 默认参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `SLICE_SIZE` | 20 | 每 20 轮 = 1 个切片 |
| `WINDOW_SIZE` | 5 | 滑动窗口保留切片数 |
| `SHORT_TERM_N` | 10 | 短期记忆轮数 |
| `EPISODIC_TOP_K` | 3 | 情景召回条数 |
| `TTL_SECONDS` | 1800 | 会话不活跃清理 |
| `MAX_INPUT_LENGTH` | 2000 | 输入最大字数 |
