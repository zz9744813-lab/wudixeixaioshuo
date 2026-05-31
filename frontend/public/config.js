/**
 * 运行时配置注入
 * 由部署脚本或 Nginx 在 HTML 之前注入，覆盖构建时的环境变量
 */
window.__APP_CONFIG__ = window.__APP_CONFIG__ || {};
window.__APP_CONFIG__.API_BASE_URL = 'http://107.172.138.14:8000/api';
window.__APP_CONFIG__.APP_API_KEY = '';
