"""公共配置：所有可调参数集中于此，业务代码禁止硬编码魔法数字。"""
import os

# ===== 业务参数 =====
SLICE_SIZE = 20          # 每 20 轮 = 1 个切片（固定分段）
CYCLE_SLICES = 5         # 人格周期 = 5 个切片（每 100 轮切换一次人格）
DEFAULT_MBTI = "general"  # 未选初始类型时的默认风格（通用兜底）
SHORT_TERM_N = 10        # 短期记忆保留最近 N 轮
EPISODIC_TOP_K = 3       # 情景记忆召回条数
TTL_SECONDS = 30 * 60    # 会话不活跃自动清理（30 分钟）
CLEANUP_INTERVAL_SECONDS = 60  # 后台清理线程扫描周期（秒）
MAX_INPUT_LENGTH = 2000  # 用户输入最大字数

# ===== LLM 接入配置（环境变量驱动，禁止硬编码密钥）=====
LLM_BACKEND = os.getenv("LLM_BACKEND", "mock")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen2.5-7b-instruct")

# ===== 全局取值域（分工前置 §5）=====
MBTI_TYPES = [
    "ISTJ", "ISFJ", "INFJ", "INTJ",
    "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP",
    "ESTJ", "ESFJ", "ENFJ", "ENTJ",
]
VALID_MBTI = MBTI_TYPES + [DEFAULT_MBTI]

EMOTIONS = ["开心", "平静", "焦虑", "悲伤", "压力大", "愤怒", "孤独"]
