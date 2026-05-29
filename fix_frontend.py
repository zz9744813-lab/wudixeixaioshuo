#!/usr/bin/env python3
"""修复前端硬编码 API 调用"""

import re
import os

replacements = [
    # EvolutionCenter.js
    ('frontend/src/pages/EvolutionCenter.js', [
        (r"const API_BASE = 'http://localhost:8000';?\n", 'import api from \'../services/api\';\n'),
        (r'fetch\(`${API_BASE}/api/evolution/`\)', 'api.get("/evolution/")'),
        (r'fetch\(`${API_BASE}/api/evolution/stats/overview`\)', 'api.get("/evolution/stats/overview")'),
        (r'fetch\(`${API_BASE}/api/evolution/best-practices`\)', 'api.get("/evolution/best-practices")'),
        (r'fetch\(`${API_BASE}/api/evolution/dimensions`\)', 'api.get("/evolution/dimensions")'),
        (r'fetch\(`${API_BASE}/api/evolution/\$\{id\}`\)', 'api.get(`/evolution/${id}`)'),
        (r'fetch\(`${API_BASE}/api/evolution/\$\{id\}/action`, \{\s*method: \'POST\',\s*headers: \{ [^}]+ \},\s*body: JSON\.stringify\(\{ action \}\),\s*\}\)', 'api.post(`/evolution/${id}/action`, { action })'),
    ]),
    # ExportPage.js
    ('frontend/src/pages/ExportPage.js', [
        (r"const API_BASE = 'http://localhost:8000';?\n", 'import api from \'../services/api\';\n'),
        (r'fetch\(`${API_BASE}/api/projects`\)', 'api.get("/projects")'),
        (r'fetch\(`${API_BASE}/api/export/formats`\)', 'api.get("/export/formats")'),
        (r'fetch\(`${API_BASE}/api/export/history[^`]*`\)', 'api.get("/export/history")'),
        (r'fetch\(`${API_BASE}/api/export/stats/word-count/\$\{[^}]+\}`\)', 'api.get(`/export/stats/word-count/${projectId}`)'),
    ]),
]

def fix_file(filepath, patterns):
    full_path = os.path.join('F:/kelaode/quanzidong', filepath)
    if not os.path.exists(full_path):
        print(f"File not found: {full_path}")
        return

    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    if content != original:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
    else:
        print(f"No changes: {filepath}")

if __name__ == '__main__':
    for filepath, patterns in replacements:
        fix_file(filepath, patterns)
