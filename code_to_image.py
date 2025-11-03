#!/usr/bin/env python3
from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import ImageFormatter
from pathlib import Path
from datetime import datetime
import sys


def main():
    # 1) CLI 인자로 원본 파일 경로 받기
    if len(sys.argv) != 2:
        print("사용법: python code_to_image.py <대상파일경로>")
        print("예시:   python code_to_image.py backend/app/main.py")
        sys.exit(1)

    input_path = Path(sys.argv[1]).resolve()

    if not input_path.exists():
        print(f"에러: 파일을 찾을 수 없음 -> {input_path}")
        sys.exit(1)

    # 2) 코드 읽기
    code_text = input_path.read_text(encoding="utf-8")

    # 3) 출력 디렉토리 준비 (homesweethome/code_to_image/)
    project_root = Path(__file__).resolve().parent  # code_to_image.py가 있는 폴더
    output_dir = project_root / "code_to_image"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 4) 타임스탬프 + 원본 파일명 그대로 살린 출력 파일명 만들기
    #    예: 20251101_003541_main.py.png
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{timestamp}_{input_path.name}.png"
    output_path = output_dir / output_filename

    # 5) 문법 하이라이터(lexer)는 파일 확장자 보고 자동 선택
    try:
        lexer = get_lexer_for_filename(str(input_path))
    except Exception:
        # 확장자 모르면 그냥 txt로 간다
        from pygments.lexers import TextLexer
        lexer = TextLexer()

    # 6) 이미지 만들기
    image_bytes = highlight(
        code_text,
        lexer,
        ImageFormatter(
            font_name="NanumGothicCoding",  # ✅ 한글 완벽 지원
            line_numbers=True,
            image_pad=20,
            line_number_bg="#f5f5f5",
            line_number_fg="#888888",
            style="friendly",
        ),
    )

    # 7) 파일 저장
    output_path.write_bytes(image_bytes)

    # 8) 완료 로그
    print("✅ 코드 → 이미지 변환 완료")
    print(f"   원본:  {input_path}")
    print(f"   저장:  {output_path}")


if __name__ == "__main__":
    main()
