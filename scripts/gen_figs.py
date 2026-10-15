# -*- coding: utf-8 -*-
"""生成方案说明书所需图片：系统总架构图 + 一轮交互数据流时序图。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


def box(ax, x, y, w, h, title, lines, fc="#E8F0FE", ec="#2A5DB0", title_fs=11, fs=9):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                       linewidth=1.6, edgecolor=ec, facecolor=fc)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h - 0.11, title, ha="center", va="center",
            fontsize=title_fs, fontweight="bold", color="#1A3A6B")
    if lines:
        body = "\n".join(lines)
        ax.text(x + w / 2, y + h / 2 - 0.02, body, ha="center", va="center",
                fontsize=fs, color="#333333", linespacing=1.5)


def arrow(ax, x1, y1, x2, y2, color="#555555"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                        mutation_scale=16, linewidth=1.6, color=color)
    ax.add_patch(a)


def fig_architecture(path):
    fig, ax = plt.subplots(figsize=(9, 12.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis("off")

    W = 7.0
    X = 1.5

    # 用户输入
    box(ax, X, 13.1, W, 0.7, "用户输入", None, fc="#FFFFFF", ec="#555555", title_fs=11)
    arrow(ax, X + W / 2, 13.1, X + W / 2, 12.55)

    # 安全风控
    box(ax, X, 11.55, W, 1.0, "安全风控（前置短路）",
        ["命中风险词 → 直接返回固定安全回复，跳过后续全部流程"], fc="#FDE7E7", ec="#C0392B")
    arrow(ax, X + W / 2, 11.55, X + W / 2, 11.0)

    # 感知路由智能体
    box(ax, X, 8.9, W, 2.1, "感知路由智能体（RouterAgent）",
        ["· 情感识别：规则词典为主 + Mock 兜底（7 类情绪）",
         "· 轮次计数 / 固定分段切片 / 滑动窗口 / 投票",
         "· MBTI 风格路由分发（16 种 + 通用兜底）"], fc="#E8F0FE", ec="#2A5DB0")
    arrow(ax, X + W / 2, 8.9, X + W / 2, 8.35)

    # 全局记忆管理智能体
    box(ax, X, 6.25, W, 2.1, "全局记忆管理智能体（MemoryAgent）",
        ["· 短期记忆：最近 N 轮原始消息",
         "· 情景记忆：全历史 + 关键词交集打分召回 top-k",
         "· 事实记忆：结构化 JSON（规则提取 + 同名覆盖）"], fc="#E6F4EA", ec="#1E7A3C")
    arrow(ax, X + W / 2, 6.25, X + W / 2, 5.7)

    # 人格对话层
    box(ax, X, 3.6, W, 2.1, "人格对话层（Prompt 区分）",
        ["· 通用兜底 + 16 种 MBTI 风格模板（共 17 套）",
         "· 共享同一个 LLMClient 抽象接口",
         "· 初赛默认 MockLLM（确定性 / 可断言 / 风格可区分）"], fc="#FFF4E5", ec="#B26A00")
    arrow(ax, X + W / 2, 3.6, X + W / 2, 3.05)

    # 情绪驱动
    box(ax, X - 0.4, 1.65, 3.4, 1.4, "情感 TTS（全 Mock）",
        ["情绪标签 → mock 音频元数据", "duration 由文本长度估算"], fc="#F3E8FD", ec="#6A2DA0")
    box(ax, X + 3.6, 1.65, 3.4, 1.4, "数字人渲染（全 Mock）",
        ["情绪标签 → 表情标识", "内置 情绪→表情 映射表"], fc="#F3E8FD", ec="#6A2DA0")
    arrow(ax, X + W / 2, 3.6, X + 1.3, 3.05)
    arrow(ax, X + W / 2, 3.6, X + 5.3, 3.05)

    # 统一响应
    box(ax, X, 0.35, W, 0.8, "统一响应结构",
        ["session_id / 情绪 / MBTI / 回复文本 / mock 音频 / mock 表情"], fc="#FFFFFF", ec="#555555")
    arrow(ax, X + 1.3, 1.65, X + W / 2, 1.15)
    arrow(ax, X + 5.3, 1.65, X + W / 2, 1.15)

    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_dataflow(path):
    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    steps = [
        ("1", "接收用户文本 + 会话 ID（空则服务端生成 uuid4）"),
        ("2", "安全风控前置检查：命中 → 短路返回固定安全回复"),
        ("3", "情感识别：规则为主 + Mock 兜底 → 情绪标签 + 强度"),
        ("4", "轮次计数 +1（在回复落库后结算）"),
        ("5", "MBTI 切片 / 滑动窗口 / 投票 → 确定当前生效 MBTI"),
        ("6", "记忆检索：短期上下文 + 情景召回 + 事实画像"),
        ("7", "人格对话生成：按 MBTI 加载 Prompt，调用 LLM 生成"),
        ("8", "回复落库并结算轮次（user + assistant 两条写记忆）"),
        ("9", "情绪驱动：回复 + 情绪 → TTS(mock) 与 渲染(mock)"),
        ("10", "返回统一响应结构"),
    ]
    n = len(steps)
    for i, (num, desc) in enumerate(steps):
        y = 6.4 - i * 0.62
        box(ax, 0.6, y - 0.28, 1.0, 0.56, num, None, fc="#DCE9FB", ec="#2A5DB0", title_fs=13)
        box(ax, 1.9, y - 0.28, 7.5, 0.56, desc, None, fc="#FFFFFF", ec="#2A5DB0", title_fs=10.5)
        if i < n - 1:
            arrow(ax, 1.1, y - 0.28, 1.1, y - 0.62 - 0.28 + 0.02)

    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    import os
    outdir = os.path.join(os.path.dirname(__file__), "..", "assets")
    os.makedirs(outdir, exist_ok=True)
    fig_architecture(os.path.join(outdir, "architecture.png"))
    fig_dataflow(os.path.join(outdir, "dataflow.png"))
    print("已生成:", os.path.abspath(outdir))
