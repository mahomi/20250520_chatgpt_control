#!/usr/bin/env python3
# apply_contextual_patch.py

import argparse
import sys

"""
- 소스를 수정해야할 경우, 소스의 내용이 많아 변경분만 출력해야할 경우에는 unified diff 포맷으로 출력해줘. (패치에 실패하지 않도록 전후 컨텍스트를 생략하지 말고 포함시켜라)

python apply_contextual_patch.py --target autogluon_rolling_window.py --patch patch.diff
"""


def main():
    args = parse_args()
    apply_patch(args.target, args.patch, args.out)


def apply_patch(target_file, patch_file, out_file=None):

    # 원본 읽기
    with open(target_file, 'r', encoding='utf-8') as f:
        orig = f.readlines()
    # diff 읽기
    with open(patch_file, 'r', encoding='utf-8') as f:
        diff_lines = f.readlines()

    hunks = load_hunks(diff_lines)
    if not hunks:
        print("적용할 hunk를 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    updated = orig
    for h in hunks:
        updated = apply_hunk(updated, h)

    # 쓰기
    out_path = out_file or target_file
    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(updated)

    print(f"패치 적용 완료: {out_path}")

def parse_args():
    p = argparse.ArgumentParser(
        description="컨텍스트 기반 unified diff를 적용하는 스크립트"
    )
    p.add_argument("-t", "--target", required=True,
                   help="패치를 적용할 원본 파일 경로")
    p.add_argument("-p", "--patch", required=True,
                   help="컨텍스트 기반 diff 파일 경로")
    p.add_argument("-o", "--out", default=None,
                   help="결과를 쓸 파일 경로 (지정 없으면 원본 덮어쓰기)")
    return p.parse_args()

class Hunk:
    def __init__(self, header):
        # header: e.g. "@@ def main():" 또는 "@@"
        self.context = header[2:].strip().rstrip(':')  # 헤더 뒤의 문자열
        self.lines = []  # diff 본문: ['-old', '+new', ' context', ...]
    def add_line(self, l): self.lines.append(l.rstrip('\n'))

def load_hunks(diff_lines):
    hunks = []
    current = None
    for raw in diff_lines:
        if raw.startswith('@@'):
            current = Hunk(raw)
            hunks.append(current)
        elif current is not None:
            if raw.startswith(('-', '+', ' ')):
                current.add_line(raw)
            # else: --- +++ 파일 구분선 등 무시
    return hunks

def apply_hunk(orig, hunk):
    """
    orig: list of 원본 라인(str, 끝에 '\n' 포함)
    hunk: Hunk 객체
    """
    # 1) 시작 위치 찾기
    if hunk.context:
        # 헤더에 붙은 컨텍스트 라인을 찾아 그 다음부터 적용
        idx = next((i for i, L in enumerate(orig) if hunk.context in L), None)
        if idx is None:
            print(f"[경고] 헤더 컨텍스트 '{hunk.context}'를 찾을 수 없어 건너뜁니다.", file=sys.stderr)
            return orig
        start = idx + 1
    else:
        # 첫 번째 '-' 라인 내용으로 위치 탐색
        first_rm = hunk.lines[0][1:]  # '-...' 에서 내용만
        # 개행 차이 무시하고 strip 비교
        idx = next((i for i, L in enumerate(orig) if L.strip() == first_rm.strip()), None)
        if idx is None:
            print(f"[경고] 삭제할 라인 '{first_rm.strip()}'을(를) 찾을 수 없어 건너뜁니다.", file=sys.stderr)
            return orig
        start = idx

    # 2) hunk 적용
    new_block = []
    orig_idx = start
    for d in hunk.lines:
        prefix, content = d[0], d[1:]
        if prefix == ' ':
            # 컨텍스트: 그대로 유지
            new_block.append(orig[orig_idx])
            orig_idx += 1
        elif prefix == '-':
            # 삭제: orig 라인만 건너뛰고 new_block에 추가 안 함
            orig_idx += 1
        elif prefix == '+':
            # 추가: new_block에만 추가
            # content가 개행 포함 안 했다면 개행 붙임
            if not content.endswith('\n'):
                content += '\n'
            new_block.append(content)
    # 3) 원본 앞/뒤와 결합
    return orig[:start] + new_block + orig[orig_idx:]

if __name__ == "__main__":
    main()
