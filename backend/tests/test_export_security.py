"""
Export Security Tests - 导出安全测试
TEST-003: 导出路径和权限安全测试（从 test_upload_security.py 分离）
"""

import pytest


class TestExportPathSecurity:
    """导出路径安全测试"""

    def test_export_download_rejects_path_traversal(self, client, api_headers):
        """导出下载拒绝路径穿越 - 必须400或404"""
        response = client.get(
            "/api/export/download/../../../etc/passwd",
            headers=api_headers
        )
        # 严格检查：不允许401
        assert response.status_code in [400, 404], f"期望400或404，实际{response.status_code}"

    def test_export_download_rejects_illegal_chars(self, client, api_headers):
        """导出下载拒绝非法字符 - 必须400"""
        response = client.get(
            "/api/export/download/file;rm -rf /",
            headers=api_headers
        )
        assert response.status_code == 400, f"期望400，实际{response.status_code}"

    def test_export_download_accepts_valid_filename(self, client, api_headers):
        """导出下载接受合法文件名 - 鉴权通过后应返回404（文件不存在）"""
        response = client.get(
            "/api/export/download/test_export.md",
            headers=api_headers
        )
        # 应该返回404（文件不存在）而非400（非法请求）或401（未鉴权）
        assert response.status_code == 404, f"期望404，实际{response.status_code}"

    def test_export_delete_rejects_path_traversal(self, client, api_headers):
        """导出删除拒绝路径穿越 - 必须400或404"""
        response = client.delete(
            "/api/export/../../../app/main.py",
            headers=api_headers
        )
        # 严格检查：不允许401，只允许400（验证失败）或404（路由不匹配）
        assert response.status_code in [400, 404], f"期望400或404，实际{response.status_code}"
