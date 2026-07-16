#!/usr/bin/env python3
"""젬또리 사용량(쿼터) 자기 보고 헬퍼 스크립트.

이 스크립트는 젬또리 CLI 세션의 PostToolUse 훅 등에서 트리거되며,
자신의 크레딧 잔량을 파악하여 health.py report를 통해 대시보드로 보고합니다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "CLAUDE.md").exists():
            return p
    return Path(__file__).resolve().parents[1]

ROOT = _find_root()
KST = timezone(timedelta(hours=9))

def get_gemttori_quota_windows() -> list[dict]:
    """젬또리 자신의 각 쿼터 창(window) 리스트를 리턴합니다.
    
    [{'label': '5시간', 'remaining_pct': int, 'resets_at': str | None}, ...]
    """
    telemetry_path = Path("/tmp/agy-telemetry.json")
    windows = []
    
    if telemetry_path.exists():
        try:
            data = json.loads(telemetry_path.read_text(encoding="utf-8"))
            quota_data = data.get("quota", {})
            
            # 5시간 쿼터
            quota_5h = quota_data.get("gemini-5h") or quota_data.get("3p-5h")
            if quota_5h:
                frac_5h = quota_5h.get("remaining_fraction")
                pct_5h = round(float(frac_5h) * 100.0) if frac_5h is not None else 100
                reset_in_sec_5h = quota_5h.get("reset_in_seconds")
                resets_at_5h = None
                if reset_in_sec_5h is not None:
                    next_reset = datetime.now(KST) + timedelta(seconds=int(reset_in_sec_5h))
                    resets_at_5h = next_reset.strftime("%m-%d %H:%M")
                windows.append({
                    "label": "5시간",
                    "remaining_pct": pct_5h,
                    "resets_at": resets_at_5h
                })
                
            # 일주일(7일) 쿼터
            quota_wk = quota_data.get("gemini-weekly") or quota_data.get("3p-weekly")
            if quota_wk:
                frac_wk = quota_wk.get("remaining_fraction")
                pct_wk = round(float(frac_wk) * 100.0) if frac_wk is not None else 100
                reset_in_sec_wk = quota_wk.get("reset_in_seconds")
                resets_at_wk = None
                if reset_in_sec_wk is not None:
                    next_reset = datetime.now(KST) + timedelta(seconds=int(reset_in_sec_wk))
                    resets_at_wk = next_reset.strftime("%m-%d %H:%M")
                windows.append({
                    "label": "7일",
                    "remaining_pct": pct_wk,
                    "resets_at": resets_at_wk
                })
                
            if windows:
                return windows
        except Exception:
            pass

    # 2. fallback: history.jsonl 기반 최근 호출 횟수로 쿼터 잔량 추정
    history_path = Path.home() / ".gemini" / "antigravity-cli" / "history.jsonl"
    if history_path.exists():
        try:
            now_dt = datetime.now(KST)
            cutoff_dt_5h = now_dt - timedelta(hours=5)
            cutoff_dt_7d = now_dt - timedelta(days=7)
            
            calls_last_5h = 0
            calls_last_7d = 0
            for line in history_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                d = json.loads(line)
                ts = d.get("timestamp")
                if ts:
                    dt = datetime.fromtimestamp(ts / 1000, KST)
                    if dt >= cutoff_dt_5h:
                        calls_last_5h += 1
                    if dt >= cutoff_dt_7d:
                        calls_last_7d += 1
            
            limit_5h = 100
            remaining_5h = max(0, round(100.0 * (1.0 - (calls_last_5h / limit_5h))))
            next_reset_5h = now_dt + timedelta(hours=5)
            
            limit_7d = 1000
            remaining_7d = max(0, round(100.0 * (1.0 - (calls_last_7d / limit_7d))))
            next_reset_7d = now_dt + timedelta(days=7)
            
            return [
                {
                    "label": "5시간",
                    "remaining_pct": remaining_5h,
                    "resets_at": next_reset_5h.strftime("%m-%d %H:%M")
                },
                {
                    "label": "7일",
                    "remaining_pct": remaining_7d,
                    "resets_at": next_reset_7d.strftime("%m-%d %H:%M")
                }
            ]
        except Exception:
            pass

    # 기본값 100%
    return [
        {
            "label": "5시간",
            "remaining_pct": 100,
            "resets_at": None
        },
        {
            "label": "7일",
            "remaining_pct": 100,
            "resets_at": None
        }
    ]

def main():
    windows = get_gemttori_quota_windows()
    
    first_rem = windows[0]["remaining_pct"] if windows else 100
    first_label = windows[0]["label"] if windows else "5시간"
    first_resets = windows[0].get("resets_at") or ""
    
    # health.py report 실행
    health_py = ROOT / "dashboard" / "engine" / "health.py"
    cmd = [
        sys.executable,
        str(health_py),
        "report",
        "--bot", "젬또리",
        "--remaining", str(first_rem),
        "--window", first_label
    ]
    if first_resets:
        cmd.extend(["--resets", first_resets])
    
    cmd.extend(["--windows-json", json.dumps(windows, ensure_ascii=False)])
    cmd.extend(["--note", "Hooks 자가보고 자동 갱신"])
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 젬또리 체력 보고 완료: {res.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 젬또리 체력 보고 실패: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
