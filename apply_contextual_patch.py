#!/usr/bin/env python3
# apply_contextual_patch.py
#
# unified-diff / git-diff 파일을 원본에 안전하게 적용합니다.
#
# 예시
#   python apply_contextual_patch.py \
#          --target rolling_window_optuna_org.py \
#          --patch  temp.patch \
#          --out    rolling_window_optuna_fixed.py
#
# --out 을 생략하면 원본 파일을 바로 덮어씁니다.

from __future__ import annotations

import argparse
import sys
from typing import List, Dict, Any

# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="unified-diff 패치를 적용합니다.")
    ap.add_argument("--target", required=True, help="원본 파일 경로")
    ap.add_argument("--patch", required=True, help="패치(diff) 파일 경로")
    ap.add_argument(
        "--out",
        help="결과 저장 경로(생략 시 원본을 덮어씀)",
    )
    return ap.parse_args()


# ──────────────────────────────────────────────────────────────
# File helpers
# ──────────────────────────────────────────────────────────────
def read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def write_lines(path: str, lines: List[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ──────────────────────────────────────────────────────────────
# Diff 파싱
# ──────────────────────────────────────────────────────────────
def parse_hunks(diff_lines: List[str]) -> List[Dict[str, Any]]:
    """
    `@@ ... @@` 로 구분되는 hunk 리스트를 반환한다.
    범위 정보(-10, +10)가 없어도 허용한다.
    """
    hunks: List[Dict[str, Any]] = []
    i, n = 0, len(diff_lines)

    while i < n:
        if diff_lines[i].startswith("@@"):
            # 헤더 줄 저장(필요 시 참고용)
            header = diff_lines[i].rstrip("\n\r")
            i += 1
            body: List[str] = []
            while i < n and not diff_lines[i].startswith("@@"):
                body.append(diff_lines[i])
                i += 1
            hunks.append({"header": header, "lines": body})
        else:
            i += 1
    return hunks


# ──────────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────────
def norm(line: str) -> str:
    """개행 제거 + 왼쪽 공백 제거 → 비교용 정규화"""
    return line.lstrip().rstrip("\n\r")


def lines_match(a: str, b: str) -> bool:
    """좌우 공백 차이는 허용(좌측)하고 내용 비교"""
    return norm(a) == norm(b)


# ──────────────────────────────────────────────────────────────
# Hunk 적용 (공백 무시 fuzzy-match)
# ──────────────────────────────────────────────────────────────
def find_hunk_position(
    orig: List[str],
    minus_lines: List[str],
) -> int | None:
    """
    삭제(-) 줄 시퀀스를 orig 에서 찾아 시작 index 반환.
    좌측 공백 차이는 무시한다.
    """
    if not minus_lines:
        return None

    minus_texts = [norm(l[1:]) for l in minus_lines]  # '-' 제거
    first = minus_texts[0]

    candidate_idxs = [
        idx
        for idx, line in enumerate(orig)
        if norm(line) == first
    ]

    for idx in candidate_idxs:
        if all(
            idx + j < len(orig) and lines_match(orig[idx + j], minus_texts[j])
            for j in range(len(minus_texts))
        ):
            return idx
    return None


def build_new_block(hunk_lines: List[str]) -> List[str]:
    """
    hunk_lines → 실제로 삽입할 줄 시퀀스
      ' '  : 그대로
      '+'  : 추가
      '-'  : 제거(미포함)
    """
    block: List[str] = []
    for raw in hunk_lines:
        tag, txt = raw[0], raw[1:]
        if tag in (" ", "+"):
            block.append(txt if txt.endswith(("\n", "\r")) else txt + "\n")
    return block


def apply_single_hunk(orig: List[str], hunk: Dict[str, Any]) -> List[str]:
    minus_lines = [l for l in hunk["lines"] if l.startswith("-")]

    # 위치 탐색
    pos = find_hunk_position(orig, minus_lines)
    if pos is None:
        hdr = hunk["header"]
        raise ValueError(f"hunk 위치를 찾지 못함: {hdr}")

    new_block = build_new_block(hunk["lines"])
    return orig[:pos] + new_block + orig[pos + len(minus_lines) :]


# ──────────────────────────────────────────────────────────────
# Patch 적용
# ──────────────────────────────────────────────────────────────
def apply_patch(target_path: str, patch_path: str, out_path: str | None) -> None:
    orig_lines = read_lines(target_path)
    diff_lines = read_lines(patch_path)

    hunks = parse_hunks(diff_lines)
    if not hunks:
        print("적용할 hunk를 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    updated = orig_lines
    for hunk in hunks:
        updated = apply_single_hunk(updated, hunk)

    write_lines(out_path or target_path, updated)
    print(f"패치 적용 완료: {out_path or target_path}")


# ──────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────
def main() -> None:
    args = parse_args()
    apply_patch(args.target, args.patch, args.out)


if __name__ == "__main__":
    main()
