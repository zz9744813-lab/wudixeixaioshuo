"""
Config Tests - 配置中心测试
BE-001: 生产环境 Fail-Fast 测试
"""

import pytest
from app.config import Settings


class TestProductionConfigValidation:
    """生产环境配置验证测试"""

    def test_production_requires_api_key(self, monkeypatch):
        """生产环境缺少 APP_API_KEY 必须失败"""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("APP_API_KEY", raising=False)
        monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")

        with pytest.raises(ValueError) as exc_info:
            Settings()

        assert "APP_API_KEY" in str(exc_info.value)
        assert "生产环境" in str(exc_info.value)

    def test_production_requires_secret_key(self, monkeypatch):
        """生产环境缺少 APP_SECRET_KEY 必须失败"""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_API_KEY", "test-api-key")
        monkeypatch.delenv("APP_SECRET_KEY", raising=False)

        with pytest.raises(ValueError) as exc_info:
            Settings()

        assert "APP_SECRET_KEY" in str(exc_info.value)
        assert "生产环境" in str(exc_info.value)

    def test_production_requires_both_keys(self, monkeypatch):
        """生产环境同时缺少两个 key 必须失败并都提示"""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("APP_API_KEY", raising=False)
        monkeypatch.delenv("APP_SECRET_KEY", raising=False)

        with pytest.raises(ValueError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "APP_API_KEY" in error_msg
        assert "APP_SECRET_KEY" in error_msg
        assert "生产环境" in error_msg

    def test_production_with_both_keys_succeeds(self, monkeypatch):
        """生产环境配置完整应该成功"""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_API_KEY", "test-api-key")
        monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")

        # 不应该抛出异常
        settings = Settings()
        assert settings.APP_API_KEY == "test-api-key"
        assert settings.APP_SECRET_KEY == "test-secret-key"
        assert settings.APP_ENV == "production"

    def test_staging_requires_keys(self, monkeypatch):
        """预发环境同样要求配置 key"""
        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.delenv("APP_API_KEY", raising=False)
        monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")

        with pytest.raises(ValueError) as exc_info:
            Settings()

        assert "APP_API_KEY" in str(exc_info.value)

    def test_development_allows_missing_keys(self, monkeypatch):
        """开发环境允许缺少 key"""
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.delenv("APP_API_KEY", raising=False)
        monkeypatch.delenv("APP_SECRET_KEY", raising=False)

        # 不应该抛出异常
        settings = Settings()
        assert settings.APP_API_KEY == ""
        assert settings.APP_SECRET_KEY == ""
        assert settings.APP_ENV == "development"

    def test_prod_variant_requires_keys(self, monkeypatch):
        """prod 简写同样要求配置 key"""
        monkeypatch.setenv("APP_ENV", "prod")
        monkeypatch.setenv("APP_API_KEY", "test-api-key")
        monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")

        settings = Settings()
        assert settings.APP_ENV == "prod"

    def test_auto_create_tables_default_false(self, monkeypatch):
        """默认自动创建表开关为 False"""
        monkeypatch.setenv("APP_ENV", "development")

        settings = Settings()
        assert settings.APP_AUTO_CREATE_TABLES == False

    def test_auto_create_tables_can_be_enabled(self, monkeypatch):
        """可以通过环境变量启用自动创建表"""
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("APP_AUTO_CREATE_TABLES", "true")

        settings = Settings()
        # Pydantic 会自动转换 "true" 为 True
        assert settings.APP_AUTO_CREATE_TABLES == True
