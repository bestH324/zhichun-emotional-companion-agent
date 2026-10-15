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
| POST | `/chat` | 对话（`session_id` 留空由服务端生成 uuid4，续接时回传；`initial_mbti` 可选） |
| POST | `/session/{id}/end` | 显式结束会话（不存在返回 404） |
| GET | `/session/stats` | 当前活跃会话数 |

### 对话请求示例

```json
POST /chat
{
  "session_id": "",
  "text": "我今天很开心",
  "initial_mbti": "ENTJ"
}
```

首次返回的 `session_id` 是服务端生成的 uuid4（不可枚举），后续对话回传该 id 以续接同一会话；`initial_mbti` 仅在首轮对话时生效。

## 运行测试

```bash
python -m pytest tests/ -q
```

覆盖：情感识别、MBTI 切片路由、三层记忆、安全风控、Mock LLM、会话管理、并发隔离、端到端链路。

## 命令行 Demo

```bash
python -m demo              # 交互式多轮对话（可选初始人格）
python -m demo --scripted   # 内置剧本自动演示（含安全拦截）
```

## 目录结构

```
app/                        # 应用主目录（全部业务代码）
├── main.py                 # FastAPI 入口 + 路由（仅编排，不含业务逻辑）
├── config.py               # 公共配置（业务参数 + LLM 接入配置）
├── schemas.py              # Pydantic 数据模型（请求/响应/消息）
├── llm/                    # LLM 接入区（换真模型只改这里，业务零改动）
│   ├── base.py             # LLMClient 抽象基类（业务唯一依赖的接口）
│   ├── mock.py             # MockLLM（初赛默认，确定性可断言）
│   ├── qwen.py             # QwenLLM 占位（决赛填真实 HTTP 调用）
│   └── factory.py          # get_llm() 工厂（按 LLM_BACKEND 分发）
├── agents/                 # 智能体层（无状态，只持只读依赖）
│   ├── router_agent.py     # 主调度编排（唯一数据流入口）
│   ├── memory_agent.py     # 记忆检索/组装（短期+情景+事实）
│   └── personality_agent.py# 人格对话层（加载 Prompt + 调 LLM）
├── modules/                # 功能模块层（各司其职的可复用单元）
│   ├── emotion.py          # 情感识别（规则词典为主 + LLM 兜底）
│   ├── session.py          # Session + SessionManager（隔离/并发/TTL）
│   ├── mbti_router.py      # MBTI 路由（切片画像/周期众数切换）
│   ├── memory_store.py     # 三层记忆存储（短期/情景/事实）
│   ├── safety.py           # 安全风控（风险词前置短路）
│   ├── tts.py              # 情感 TTS（全 Mock，返回音频元数据）
│   └── avatar.py           # 数字人渲染（全 Mock，情绪→表情映射）
└── prompts/                # Prompt 模板层
    └── mbti_prompts.py     # 16 种 MBTI + 通用兜底 Prompt 模板
├── tests/                  # 测试套件（9 个文件，85 项用例）
├── assets/                 # 文档图片资源（架构图/数据流图）
├── scripts/                # 文档生成脚本（画图/组装 docx）
├── demo.py                 # 命令行演示脚本（python -m demo）
├── requirements.txt        # 依赖清单
└── README.md               # 运行说明（本文档）
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
| `CYCLE_SLICES` | 5 | 人格周期 = 5 个切片（每 100 轮切换一次人格） |
| `SHORT_TERM_N` | 10 | 短期记忆轮数 |
| `EPISODIC_TOP_K` | 3 | 情景召回条数 |
| `TTL_SECONDS` | 1800 | 会话不活跃清理 |
| `MAX_INPUT_LENGTH` | 2000 | 输入最大字数 |
