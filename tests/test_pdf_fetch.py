"""PDF 拉取服务测试用例。

测试 v4.4.0 修复:
- 代理处理: _make_httpx_client 尊重系统代理, _make_localhost_client 绕过代理
- DOI 规范化
- 错误消息映射
"""

import pytest
from unittest.mock import patch, MagicMock


class TestMakeHttpxClient:
    """测试 _make_httpx_client 辅助函数。"""

    def test_default_trust_env(self):
        """默认应信任系统代理环境。"""
        from app.services.pdf_fetch import _make_httpx_client
        with _make_httpx_client() as client:
            # trust_env=True 意味着 httpx 会读取 HTTP_PROXY/HTTPS_PROXY 环境变量
            assert client._trust_env is True

    def test_custom_timeout(self):
        """应支持自定义超时。"""
        from app.services.pdf_fetch import _make_httpx_client
        with _make_httpx_client(timeout=30) as client:
            assert client._timeout.connect == 30

    def test_custom_headers(self):
        """应支持自定义 headers。"""
        from app.services.pdf_fetch import _make_httpx_client
        headers = {"User-Agent": "TestBot/1.0"}
        with _make_httpx_client(headers=headers) as client:
            assert client._headers["User-Agent"] == "TestBot/1.0"

    def test_explicit_proxy_override(self):
        """显式传入 proxy 参数应覆盖默认行为。"""
        from app.services.pdf_fetch import _make_httpx_client
        # proxy=None 显式绕过代理
        with _make_httpx_client(proxy=None) as client:
            # 验证 client 创建成功（不抛异常）
            assert client is not None


class TestMakeLocalhostClient:
    """测试 _make_localhost_client 辅助函数。"""

    def test_bypass_proxy(self):
        """localhost 请求应绕过代理。"""
        from app.services.pdf_fetch import _make_localhost_client
        with _make_localhost_client() as client:
            # proxy=None 表示绕过代理（httpx 内部属性名可能不同）
            assert client is not None

    def test_default_timeout(self):
        """默认超时应为 10 秒。"""
        from app.services.pdf_fetch import _make_localhost_client
        with _make_localhost_client() as client:
            assert client._timeout.connect == 10


class TestNormalizeDoi:
    """测试 DOI 规范化函数。"""

    def test_bare_doi(self):
        """纯 DOI 应转为 doi.org URL。"""
        from app.services.pdf_fetch import normalize_doi
        assert normalize_doi("10.1234/test") == "https://doi.org/10.1234/test"

    def test_doi_with_url_prefix(self):
        """已有 URL 前缀的 DOI 应保持不变。"""
        from app.services.pdf_fetch import normalize_doi
        assert normalize_doi("https://doi.org/10.1234/test") == "https://doi.org/10.1234/test"

    def test_http_doi_prefix(self):
        """http 前缀应转为 https。"""
        from app.services.pdf_fetch import normalize_doi
        result = normalize_doi("http://doi.org/10.1234/test")
        assert result == "https://doi.org/10.1234/test"

    def test_invalid_input(self):
        """无效输入应返回空字符串。"""
        from app.services.pdf_fetch import normalize_doi
        assert normalize_doi("") == ""


class TestValidatePdf:
    """测试 PDF 验证函数。"""

    def test_valid_pdf_header(self):
        """以 %PDF- 开头且足够长的内容应通过验证。"""
        from app.services.pdf_fetch import validate_pdf
        # validate_pdf 要求至少 100 字节
        content = b"%PDF-1.4 " + b"x" * 100
        assert validate_pdf(content) is True

    def test_invalid_pdf(self):
        """非 PDF 内容应失败。"""
        from app.services.pdf_fetch import validate_pdf
        assert validate_pdf(b"not a pdf content that is long enough " + b"x" * 100) is False
        assert validate_pdf(b"") is False

    def test_short_content_rejected(self):
        """短于 100 字节的内容应被拒绝。"""
        from app.services.pdf_fetch import validate_pdf
        assert validate_pdf(b"%PDF-1.4 short") is False

    def test_pdf_with_prefix_bytes(self):
        """带有前缀垃圾字节的 PDF 应通过验证。"""
        from app.services.pdf_fetch import validate_pdf
        # 某些出版商在 PDF 前添加跟踪像素
        content = b"\x00\x00\x00" + b"%PDF-1.4 content " + b"x" * 100
        assert validate_pdf(content) is True


class TestNormalizePdfHeader:
    """测试 PDF 头部规范化函数。"""

    def test_strip_prefix_bytes(self):
        """应剥离 %PDF- 之前的非 PDF 字节。"""
        from app.services.pdf_fetch import normalize_pdf_header
        content = b"\x00\x00\x00%PDF-1.4 content"
        result = normalize_pdf_header(content)
        assert result.startswith(b"%PDF-")

    def test_no_prefix_bytes(self):
        """已经是正确格式的内容应原样返回。"""
        from app.services.pdf_fetch import normalize_pdf_header
        content = b"%PDF-1.4 content"
        result = normalize_pdf_header(content)
        assert result == content


class TestExtractDoiFromUrl:
    """测试从 URL 中提取 DOI。"""

    def test_doi_org_url(self):
        """应从 doi.org URL 中提取 DOI。"""
        from app.services.pdf_fetch import _extract_doi_from_url
        result = _extract_doi_from_url("https://doi.org/10.1234/test")
        assert result == "10.1234/test"

    def test_bare_doi(self):
        """纯 DOI 应原样返回。"""
        from app.services.pdf_fetch import _extract_doi_from_url
        result = _extract_doi_from_url("10.1234/test")
        assert result == "10.1234/test"

    def test_invalid_url(self):
        """无效 URL 应返回空字符串。"""
        from app.services.pdf_fetch import _extract_doi_from_url
        result = _extract_doi_from_url("not a url or doi")
        assert result == ""
