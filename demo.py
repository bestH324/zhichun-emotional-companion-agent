"""命令行演示脚本：python -m demo 跑多轮对话，展示完整数据流。

用法：
    python -m demo                # 交互式多轮对话
    python -m demo --scripted     # 内置剧本自动演示（无交互）
"""
import sys

# Windows 下强制 stdout 用 UTF-8，避免中文乱码（支持 Windows Terminal / VS Code）
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.agents.router_agent import process_chat
from app.modules.session import session_manager


def _print_turn(data: dict) -> None:
    emo = data["emotion"]
    print(f"[情绪] {emo['emotion']} (强度 {emo['intensity']:.1f})")
    print(f"[MBTI] {data['mbti']}")
    print(f"[轮次] {data['turn_count']}")
    print(f"[表情] {data['expression']['expression']}")
    print(f"[音频] {data['audio']['path']}")
    print(f"芝春: {data['reply']}")
    print("-" * 50)


def run_interactive() -> None:
    print("=== 芝春情感陪伴数字人 Demo ===")
    print("可选初始人格（16 种 MBTI 之一，回车跳过则用通用兜底 general）：")
    initial = input("初始人格: ").strip().upper() or None
    print("输入消息开始对话；输入 /quit 退出\n")
    sid = ""
    first = True
    while True:
        try:
            raw = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见～")
            break
        if not raw:
            continue
        if raw.lower() in ("/quit", "/exit"):
            print("再见～")
            break
        # 仅首轮传 initial_mbti
        init = initial if first else None
        first = False
        data = process_chat(sid, raw, init).model_dump()
        sid = data["session_id"]
        _print_turn(data)
        print()


def run_scripted() -> None:
    print("=== 芝春情感陪伴数字人 Demo（脚本模式）===\n")
    script = [
        "我叫小林，今天心情有点低落",
        "我喜欢在周末去公园散步",
        "最近工作压力大，喘不过气",
        "你能陪我说说话吗？",
    ]
    sid = ""
    for i, line in enumerate(script):
        print(f"你: {line}")
        # 首轮传入初始人格 ENTJ
        init = "ENTJ" if i == 0 else None
        data = process_chat(sid, line, init).model_dump()
        sid = data["session_id"]
        _print_turn(data)
        print()
    # 演示安全风控
    print("你: 我想自杀")
    data = process_chat(sid, "我想自杀").model_dump()
    print(f"[安全拦截] {data['safety_triggered']}")
    print(f"芝春: {data['reply']}")
    print(f"\n当前活跃会话数: {session_manager.count()}")


if __name__ == "__main__":
    if "--scripted" in sys.argv:
        run_scripted()
    else:
        run_interactive()
