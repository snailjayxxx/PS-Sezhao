#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="使用真实负片/RAW 非破坏验证 PS-Sezhao 的缩略图、代理、完整解码和转正流程。",
    )
    parser.add_argument("inputs", nargs="+", help="图像文件或胶卷文件夹")
    parser.add_argument("--output", required=True, help="报告与审阅图输出目录")
    parser.add_argument("--max-files", type=int, default=None, help="最多验证多少张，默认全部")
    parser.add_argument("--no-recursive", action="store_true", help="文件夹不递归扫描")
    parser.add_argument("--proxy-only", action="store_true", help="不执行完整分辨率解码")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repository_root = Path(__file__).resolve().parents[1]
    standalone_root = repository_root / "standalone"
    sys.path.insert(0, str(standalone_root))

    from ps_sezhao.validation import validate_real_roll

    output = Path(args.output).expanduser()
    report = validate_real_roll(
        args.inputs,
        output,
        recursive=not args.no_recursive,
        max_files=args.max_files,
        full_decode=not args.proxy_only,
    )
    json_path = report.write_json(output / "real-roll-report.json")
    markdown_path = report.write_markdown(output / "real-roll-report.md")
    print(
        f"real-roll-validation: {'ok' if report.ok else 'failed'} "
        f"total={report.total} succeeded={report.succeeded} failed={report.failed} "
        f"warnings={report.warnings} elapsed={report.elapsed_seconds:.2f}s"
    )
    print(f"json={json_path}")
    print(f"markdown={markdown_path}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
