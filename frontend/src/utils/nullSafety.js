/**
 * 前端空值安全工具函数
 * 统一处理异步数据加载中的 null/undefined 兜底
 */

/**
 * 将任意值转换为对象
 * @param {*} value - 任意值
 * @returns {object} 保证返回对象
 */
export function toObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

/**
 * 将任意值转换为数组
 * @param {*} value - 任意值
 * @returns {Array} 保证返回数组
 */
export function toArray(value) {
  return Array.isArray(value) ? value : [];
}

/**
 * 将任意值安全转换为数字
 * @param {*} value - 任意值
 * @param {number} fallback - 兜底值（默认 0）
 * @returns {number} 有效数字或兜底值
 */
export function toNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}
