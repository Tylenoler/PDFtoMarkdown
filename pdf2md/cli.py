"""CLI entry point with argparse."""

import argparse
import sys
from pathlib import Path

from pdf2md.converter import Converter
from pdf2md.utils.helpers import collect_pdf_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf2md",
        description="Convert PDF files to structured Markdown with images.",
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="?",
        default=None,
        help="PDF file or directory containing PDFs (use --batch for directories)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all PDFs in the input directory",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="ch",
        help="OCR language (default: ch)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Render DPI for OCR (default: 300)",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU even if GPU is available",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start Web UI (open in browser) instead of CLI mode",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Start native desktop GUI window",
    )
    return parser


def run_cli(args: argparse.Namespace) -> int:
    """Execute CLI conversion based on parsed arguments."""
    if args.input is None:
        print("Error: input file or directory required for CLI mode")
        return 1

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: input not found: {input_path}")
        return 1

    # Collect PDFs
    if args.batch:
        pdfs = collect_pdf_files(input_path)
        if not pdfs:
            print(f"No PDF files found in {input_path}")
            return 1
    else:
        if input_path.is_dir():
            print("Error: input is a directory. Use --batch to process all PDFs in a directory.")
            return 1
        pdfs = [input_path]

    # Convert each
    use_gpu = not args.cpu
    for pdf in pdfs:
        output_sub = Path(args.output) / pdf.stem
        print(f"Converting: {pdf.name} → {output_sub}/")
        converter = Converter(
            output_dir=output_sub,
            lang=args.lang,
            use_gpu=use_gpu,
            dpi=args.dpi,
        )
        report = converter.convert(pdf)
        print(f"  Done — {report['page_count']} pages, {report['output_md']}")

    return 0


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.gui:
        from pdf2md.gui import start_gui
        start_gui()
        return

    if args.web:
        from pdf2md.web import start_web
        start_web(host="127.0.0.1", port=5000)
        return

    sys.exit(run_cli(args))
