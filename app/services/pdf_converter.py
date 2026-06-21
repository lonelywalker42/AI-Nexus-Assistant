"""PDF → Markdown 结构化转换服务 — MinerU + PyMuPDF 三级降级

转换策略:
  1. MinerU 可用 → magic_pdf 转换（保留公式/图片/表格/版面）
  2. MinerU 不可用 → PyMuPDF 提取纯文本 Markdown
"""

import os
import logging
from pathlib import Path
from typing import Optional

_log = logging.getLogger("nexus.pdf_converter")


def check_mineru_available() -> bool:
    """检测 MinerU (magic-pdf) 是否已安装"""
    try:
        import magic_pdf  # noqa: F401
        return True
    except ImportError:
        return False


def get_mineru_version() -> str:
    """获取 MinerU 版本号"""
    try:
        import magic_pdf
        return getattr(magic_pdf, "__version__", "unknown")
    except ImportError:
        return ""


def convert_pdf_to_markdown(pdf_path: str, output_dir: str) -> dict:
    """自动选择转换器将 PDF 转为 Markdown。

    优先使用 MinerU（高质量），降级到 PyMuPDF（基础质量）。

    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录

    Returns:
        dict: {method, output_path, pages, success, error}
    """
    if not os.path.exists(pdf_path):
        return {"success": False, "error": f"PDF 文件不存在: {pdf_path}"}

    os.makedirs(output_dir, exist_ok=True)

    # 优先尝试 MinerU
    if check_mineru_available():
        try:
            result = _convert_with_mineru(pdf_path, output_dir)
            if result.get("success"):
                return result
            _log.warning(f"MinerU 转换失败，降级到 PyMuPDF: {result.get('error')}")
        except Exception as e:
            _log.warning(f"MinerU 转换异常，降级到 PyMuPDF: {e}")

    # 降级到 PyMuPDF
    return _convert_with_pymupdf(pdf_path, output_dir)


def _convert_with_mineru(pdf_path: str, output_dir: str) -> dict:
    """使用 MinerU (magic-pdf) 转换 PDF → Markdown。

    保留 LaTeX 公式、Markdown 表格、图片引用、章节层级。
    """
    try:
        from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
        from magic_pdf.pipe.UNIPipe import UNIPipe
        from magic_pdf.pipe.OCRPipe import OCRPipe

        pdf_name = Path(pdf_path).stem
        image_dir = os.path.join(output_dir, f"{pdf_name}_images")
        os.makedirs(image_dir, exist_ok=True)

        # 读取 PDF
        reader = FileBasedDataReader("")
        pdf_bytes = reader.read(pdf_path)

        # 图片写入器
        image_writer = FileBasedDataWriter(image_dir)
        md_writer = FileBasedDataWriter(output_dir)

        # 尝试 UNIPipe（自动检测文本/扫描）
        try:
            pipe = UNIPipe(pdf_bytes, [], image_writer, is_debug=False)
            pipe.pipe_classify()
            pipe.pipe_analyze()
            pipe.pipe_parse()
            md_content = pipe.pipe_mk_markdown(image_dir, drop_mode="none")
        except Exception:
            # 降级到 OCR 管线
            _log.info("UNIPipe 失败，尝试 OCRPipe")
            pipe = OCRPipe(pdf_bytes, [], image_writer)
            pipe.pipe_classify()
            pipe.pipe_analyze()
            pipe.pipe_parse()
            md_content = pipe.pipe_mk_markdown(image_dir, drop_mode="none")

        # 写入 Markdown 文件
        output_path = os.path.join(output_dir, f"{pdf_name}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # 获取页数
        pages = 0
        try:
            import fitz
            doc = fitz.open(pdf_path)
            pages = len(doc)
            doc.close()
        except Exception:
            pass

        return {
            "success": True,
            "method": "mineru",
            "output_path": output_path,
            "pages": pages,
            "image_dir": image_dir,
        }

    except ImportError as e:
        return {"success": False, "error": f"MinerU 依赖缺失: {e}"}
    except Exception as e:
        return {"success": False, "error": f"MinerU 转换失败: {e}"}


def _convert_with_pymupdf(pdf_path: str, output_dir: str) -> dict:
    """使用 PyMuPDF 降级提取纯文本 Markdown。

    逐页提取文本块，按阅读顺序排列（处理双栏），
    输出纯文本 Markdown（无公式/图片）。
    """
    try:
        import fitz
    except ImportError:
        return {"success": False, "error": "PyMuPDF 未安装，请运行: pip install pymupdf"}

    pdf_name = Path(pdf_path).stem
    output_path = os.path.join(output_dir, f"{pdf_name}.md")

    try:
        doc = fitz.open(pdf_path)
        pages = len(doc)
        md_parts = []

        for page_num, page in enumerate(doc, 1):
            blocks = page.get_text("blocks")
            # 按 y 坐标排序，再按 x 坐标（处理双栏）
            blocks = sorted(blocks, key=lambda b: (round(b[1] / 10) * 10, b[0]))

            page_text = []
            for block in blocks:
                if block[6] == 0:  # 文本块
                    text = block[4].strip()
                    if text:
                        page_text.append(text)

            if page_text:
                md_parts.append(f"\n<!-- Page {page_num} -->\n")
                md_parts.append("\n\n".join(page_text))

        doc.close()

        md_content = "\n".join(md_parts)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {
            "success": True,
            "method": "pymupdf",
            "output_path": output_path,
            "pages": pages,
        }

    except Exception as e:
        return {"success": False, "error": f"PyMuPDF 转换失败: {e}"}


def batch_convert_pdfs(pdf_dir: str, output_dir: str) -> list[dict]:
    """批量转换目录下所有 PDF。

    Args:
        pdf_dir: PDF 文件目录
        output_dir: Markdown 输出目录

    Returns:
        list[dict]: 每个文件的转换结果
    """
    results = []
    pdf_dir_path = Path(pdf_dir)
    if not pdf_dir_path.exists():
        return [{"success": False, "error": f"目录不存在: {pdf_dir}"}]

    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    _log.info(f"批量转换: 找到 {len(pdf_files)} 个 PDF 文件")

    for pdf_file in pdf_files:
        try:
            result = convert_pdf_to_markdown(str(pdf_file), output_dir)
            result["source"] = str(pdf_file)
            results.append(result)
        except Exception as e:
            results.append({
                "success": False,
                "source": str(pdf_file),
                "error": str(e),
            })

    return results
