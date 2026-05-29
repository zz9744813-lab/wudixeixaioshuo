#!/usr/bin/env python3
"""批量修复前端硬编码 API 调用"""

import re
import os

# 文件路径 -> [(pattern, replacement), ...]
REPLACEMENTS = {
    'frontend/src/pages/Projects.js': [
        (r"import \{ API_BASE_URL \} from '\.\./services/api';\n", "import api from '../services/api';\n"),
        (r'fetch\(`\$\{API_BASE_URL\}/projects/`\)', 'api.get("/projects/")'),
        (r'fetch\(`\$\{API_BASE_URL\}/projects/`, \{', 'api.post("/projects/", '),
    ],
    'frontend/src/pages/ProjectDetail.js': [
        (r"import \{ API_BASE_URL \} from '\.\./services/api';\n", "import api from '../services/api';\n"),
        (r'fetch\(`\$\{API_BASE_URL\}/projects/\$\{id\}`\)', 'api.get(`/projects/${id}`)'),
        (r'await fetch\(`\$\{API_BASE_URL\}/projects/\$\{id\}/start`, \{ method: \'POST\' \}\)', 'await api.post(`/projects/${id}/start`)'),
        (r'await fetch\(`\$\{API_BASE_URL\}/projects/\$\{id\}/pause`, \{ method: \'POST\' \}\)', 'await api.post(`/projects/${id}/pause`)'),
    ],
    'frontend/src/pages/Tasks.js': [
        (r"import \{ API_BASE_URL \} from '\.\./services/api';\n", "import api from '../services/api';\n"),
        (r'fetch\(`\$\{API_BASE_URL\}/tasks/`\)', 'api.get("/tasks/")'),
    ],
    'frontend/src/pages/ModelConfig.js': [
        (r"import \{ API_BASE_URL \} from '\.\./services/api';\n", "import api from '../services/api';\n"),
        (r'fetch\(`\$\{API_BASE_URL\}/models/providers`\)', 'api.get("/models/providers")'),
        (r'fetch\(`\$\{API_BASE_URL\}/models/providers`,', 'api.post("/models/providers",'),
        (r'fetch\(`\$\{API_BASE_URL\}/models/providers/\$\{id\}/test`,', 'api.post(`/models/providers/${id}/test`,'),
    ],
    'frontend/src/pages/Techniques.js': [
        (r"import \{ API_BASE_URL \} from '\.\./services/api';\n", "import api from '../services/api';\n"),
        (r'fetch\(`\$\{API_BASE_URL\}/techniques/`\)', 'api.get("/techniques/")'),
    ],
    'frontend/src/pages/UsageDashboard.js': [
        (r"import \{ API_BASE_URL \} from '\.\./services/api';\n", "import api from '../services/api';\n"),
        (r'fetch\(`\$\{API_BASE_URL\}/usage/summary', 'api.get("/usage/summary'),
        (r'fetch\(`\$\{API_BASE_URL\}/usage/by-role', 'api.get("/usage/by-role'),
        (r'fetch\(`\$\{API_BASE_URL\}/usage/by-model', 'api.get("/usage/by-model'),
        (r'fetch\(`\$\{API_BASE_URL\}/usage/daily', 'api.get("/usage/daily'),
    ],
}

def fix_file(filepath, patterns):
    base = 'F:/kelaode/quanzidong'
    full_path = os.path.join(base, filepath)

    if not os.path.exists(full_path):
        print(f"Not found: {filepath}")
        return

    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    if content != original:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
    else:
        print(f"No changes: {filepath}")

if __name__ == '__main__':
    for filepath, patterns in REPLACEMENTS.items():
        fix_file(filepath, patterns)
