"""下载情感陪伴微调数据集到 F:/芝春智能体/datasets/（走 hf-mirror 镜像）。"""
import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from huggingface_hub import hf_hub_download

BASE = os.path.join(os.path.dirname(__file__), "..", "datasets")
BASE = os.path.abspath(BASE)

# (repo_id, 文件名, 保存子目录)
FILES = [
    # BeyondDialogue —— 角色扮演「人设→对话」对齐（中文三件套）
    ("yuyouyu/BeyondDialogue", "RPA_CN_SFT.json", "beyond_dialogue"),
    ("yuyouyu/BeyondDialogue", "RP_CN_SFT.json", "beyond_dialogue"),
    ("yuyouyu/BeyondDialogue", "CSERP_CN_SFT.json", "beyond_dialogue"),
    # roleplayLLM_Chinese —— 中文角色扮演
    ("BigPancake01/roleplayLLM_Chinese", "roleplay.json", "roleplay_llm"),
    # PsyQA —— 中文心理支持问答（MIT 镜像版）
    ("ghjkgk45bhj/PsyQA", "train.json", "psyqa"),
    ("ghjkgk45bhj/PsyQA", "valid.json", "psyqa"),
    ("ghjkgk45bhj/PsyQA", "test.json", "psyqa"),
]


def main():
    for repo, filename, subdir in FILES:
        dest_dir = os.path.join(BASE, subdir)
        os.makedirs(dest_dir, exist_ok=True)
        print(f"[下载] {repo}/{filename} -> {dest_dir}", flush=True)
        try:
            path = hf_hub_download(
                repo_id=repo,
                filename=filename,
                repo_type="dataset",
                local_dir=dest_dir,
                local_dir_use_symlinks=False,
            )
            size = os.path.getsize(path) / 1024 / 1024
            print(f"[完成] {filename}  {size:.1f}MB", flush=True)
        except Exception as e:
            print(f"[失败] {repo}/{filename}: {e}", flush=True)
    print("全部下载任务结束", flush=True)


if __name__ == "__main__":
    main()
