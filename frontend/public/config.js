/**
 * 运行时配置注入
 * 部署脚本 / Nginx / 容器入口脚本可在 HTML 之前注入 window.__APP_CONFIG__
 * 覆盖此文件中的默认值。
 *
 * 优先级:
 *   1. window.__APP_CONFIG__ (部署时注入，覆盖一切)
 *   2. REACT_APP_API_URL 构建期环境变量
 *   3. 留空 → 前端在 api.js 中回退到 window.location.origin + '/api'（相对路径）
 *
 * 注意: 这里的默认值故意留空字符串，确保开箱即用在任何域名/IP 都能工作。
 */
window.__APP_CONFIG__ = window.__APP_CONFIG__ || {};
window.__APP_CONFIG__.API_BASE_URL = window.__APP_CONFIG__.API_BASE_URL || '';
window.__APP_CONFIG__.APP_API_KEY = window.__APP_CONFIG__.APP_API_KEY || '';
