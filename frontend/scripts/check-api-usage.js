/**
 * Check API Usage - 检查前端 API 使用规范
 * 禁止：硬编码 localhost:8000、直接使用 fetch、使用原生 EventSource
 */

const fs = require('fs');
const path = require('path');

const forbiddenPatterns = [
  { pattern: "const API_BASE = 'http://localhost:8000'", desc: "硬编码 API_BASE" },
  { pattern: 'fetch(`${API_BASE}', desc: "直接使用 fetch 拼接 API_BASE" },
  { pattern: 'new EventSource', desc: "使用原生 EventSource（应该用 @microsoft/fetch-event-source）" },
  { pattern: 'http://localhost:8000/api', desc: "硬编码 localhost API 地址" },
  { pattern: "window.open(`/api/", desc: "直接打开受保护 API URL，无法携带 X-API-Key" },
  { pattern: "window.open('/api/", desc: "直接打开受保护 API URL，无法携带 X-API-Key" },
];

const excludeFiles = [
  'src/services/api.js',
  'src/services/eventStream.js',
  'src/setupTests.js',
  'src/reportWebVitals.js',
];

function walk(dir) {
  const results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    const relativePath = path.relative('src', fullPath).replace(/\\/g, '/');

    if (entry.isDirectory()) {
      results.push(...walk(fullPath));
    } else if (entry.isFile() && fullPath.endsWith('.js')) {
      // 排除白名单文件
      const shouldExclude = excludeFiles.some(ex => relativePath.includes(ex));
      if (!shouldExclude) {
        results.push(fullPath);
      }
    }
  }

  return results;
}

function main() {
  const srcDir = path.join(__dirname, '..', 'src');

  if (!fs.existsSync(srcDir)) {
    console.error('❌ 未找到 src 目录:', srcDir);
    process.exit(1);
  }

  const files = walk(srcDir);
  let hasError = false;

  for (const file of files) {
    const content = fs.readFileSync(file, 'utf8');
    const relativePath = path.relative(path.join(__dirname, '..'), file);

    for (const { pattern, desc } of forbiddenPatterns) {
      if (content.includes(pattern)) {
        console.error(`❌ ${relativePath}`);
        console.error(`   禁止: ${desc}`);
        console.error(`   发现: ${pattern}`);
        hasError = true;
      }
    }
  }

  if (hasError) {
    console.error('\n❌ 检查失败：发现禁止的 API 使用模式');
    console.error('请使用 src/services/api.js 进行 API 调用');
    process.exit(1);
  } else {
    console.log('✅ 前端 API 使用检查通过');
    process.exit(0);
  }
}

main();
