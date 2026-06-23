"""共享测试配置和 fixtures。"""

import os
import sys
import pytest

# 确保 app 包可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def tmp_pdf_dir(tmp_path):
    """提供临时 PDF 输出目录。"""
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    return str(pdf_dir)
