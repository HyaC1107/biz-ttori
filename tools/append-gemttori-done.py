#!/usr/bin/env python3
"""젬또리 세션 종료 시 감사 로그(events.jsonl) 기록 헬퍼 스크립트.

이 스크립트는 젬또리 CLI 세션의 Stop 훅에서 트리거되며,
세션 내에서 수정한 파일 이력을 분석하여 events.jsonl에 bot.done 이벤트를 기록합니다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "CLAUDE.md").exists():
            return p
    return Path(__file__).resolve().parents[1]

ROOT = _find_root()

def get_recent_modified_summary() -> str:
    """최근 30분 이내에 수정된 스펙/기획/일지 파일들을 분석하여 요약문구를 만듭니다."""
    now = time.time()
    modified_files = []
    
    # daily, projects, specs 폴더 스캔
    for folder in ("daily", "projects", "specs"):
        folder_path = ROOT / folder
        if not folder_path.is_dir():
            continue
        for p in folder_path.rglob("*.md"):
            try:
                st = p.stat()
                # 30분(1800초) 이내 수정된 파일
                if now - st.st_mtime < 1800:
                    modified_files.append(p.relative_to(ROOT).as_posix())
            except OSError:
                continue
                
    if not modified_files:
        # 수정 파일이 없으면 최근 git commit 메시지 참조
        try:
            res = subprocess.run(
                ["git", "log", "-n", "1", "--pretty=format:%s"],
                capture_output=True, text=True, check=True
            )
            return f"세션 종료 (최근 작업: {res.stdout.strip()})"
        except Exception:
            return "젬또리 CLI 세션 작업 완료"
            
    # 수정된 파일 기반으로 요약
    files_str = ", ".join(modified_files[:2])
    if len(modified_files) > 2:
        files_str += f" 외 {len(modified_files) - 2}건"
    return f"{files_str} 문서 작성 및 검토 완료"

def main():
    summary = get_recent_modified_summary()
    
    # events.py append 실행
    events_py = ROOT / "dashboard" / "engine" / "events.py"
    
    # 수정한 파일 중 프로젝트가 명시되어 있다면 해당 프로젝트 추출
    project = None
    if "projects/fanbird" in summary:
        project = "fanbird-broadcast"
    elif "projects/close" in summary:
        project = "close"
    elif "projects/FMS" in summary:
        project = "FMS"
        
    cmd = [
        sys.executable,
        str(events_py),
        "append",
        "--type", "bot.done",
        "--actor", "젬또리",
        "--dept", "ops",
        "--summary", summary
    ]
    if project:
        cmd.extend(["--project", project])
        
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 젬또리 감사 로그 기록 완료: {res.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 젬또리 감사 로그 기록 실패: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
