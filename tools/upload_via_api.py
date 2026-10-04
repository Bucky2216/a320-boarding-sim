# 上传通道：本机 git 传输（github.com/<repo>.git）被网络阻断时，
# 改用 GitHub Contents API（api.github.com）把文件写进仓库。
#
# 用法：
#   python3 tools/upload_via_api.py                    # 上传全部文件
#   python3 tools/upload_via_api.py index.html         # 只上传指定文件（可多个）
#
# 脚本会自动查询远程文件的 sha 再提交，因此可以重复运行做覆盖更新。
import base64
import json
import os
import subprocess
import sys

REPO = "Bucky2216/a320-boarding-sim"
# 以脚本所在位置推算项目根目录，换机器/换路径也能直接用
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    ("README.md", "文档：在线地址、模型说明与更新方式"),
    ("index.html", "应用本体：单文件 A320 登机模拟"),
    ("tools/upload_via_api.py", "备用上传通道（git 被阻断时使用）"),
]

TARGETS = sys.argv[1:] or [p for p, _ in FILES]


def current_sha(path):
    """取远程文件的 sha（文件不存在时返回 None），用于覆盖更新。"""
    proc = subprocess.run(
        ["gh", "api", "repos/%s/contents/%s" % (REPO, path), "--jq", ".sha"],
        capture_output=True, text=True,
    )
    sha = (proc.stdout or "").strip()
    return sha if proc.returncode == 0 and len(sha) == 40 else None


for path in TARGETS:
    desc = dict(FILES).get(path, "update")
    full = os.path.join(ROOT, path)
    with open(full, "rb") as f:
        content = base64.b64encode(f.read()).decode("ascii")
    payload = {
        "message": "add: %s（%s）" % (path, desc),
        "content": content,
        "branch": "main",
    }
    sha = current_sha(path)
    if sha:
        payload["sha"] = sha                      # 已存在则带上 sha，表示覆盖更新
        payload["message"] = "update: %s（%s）" % (path, desc)
    tmp = "/tmp/gh_payload_%s.json" % path.replace("/", "_")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    proc = subprocess.run(
        ["gh", "api", "-X", "PUT", "repos/%s/contents/%s" % (REPO, path), "--input", tmp],
        capture_output=True, text=True,
    )
    out = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    ok = "OK" if proc.returncode == 0 else "FAIL"
    print("%-26s %s  %s" % (path, ok, out.splitlines()[0][:120] if out else ""))
