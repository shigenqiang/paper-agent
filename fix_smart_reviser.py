#!/usr/bin/env python3
"""Fix smart_reviser.py by updating _clean_text_output"""

FILE_PATH = 'D:/pycharmprojects/pythonProject1/src/agents_v2/writing/smart_reviser.py'

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the method start and end
start_marker = "    def _clean_text_output(self, text: str) -> str:"
end_marker = "    def _parse_diagnosis_response"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print(f"ERROR: Could not find method boundaries")
    exit(1)

old_method = content[start_idx:end_idx]
print(f"Found method, length: {len(old_method)}")

# Build new method line by line
lines = [
    "    def _clean_text_output(self, text: str) -> str:",
    '        """清理文本输出，移除思考块、代码块标记、诊断信息等无用部分"""',
    "        if not text:",
    "            return text",
    "        import re",
    "",
    "        # 0. 处理空响应或非文本响应",
    "        if text.strip().startswith('<!') or text.strip().startswith('<html'):",
    '            return ""',
    "",
    "        # 1. 移除思考块",
    "        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)",
    "",
    "        # 2. 移除 markdown 代码块标记",
    "        text = re.sub(r'```json\\s*', '', text)",
    "        text = re.sub(r'```\\s*', '', text)",
    "        text = re.sub(r'```$', '', text)",
    "",
    "        # 3. 移除诊断相关字段",
    '        text = re.sub(r\'"diagnosis"\\s*:.*?(?="[a-z_]+"\\s*:|\\}\\s*$)', "", text, flags=re.DOTALL)',
    '        text = re.sub(r\'"grammar_issues"\\s*:.*?(?="[a-z_]+"\\s*:|\\}\\s*$|\\])', "", text, flags=re.DOTALL)',
    '        text = re.sub(r\'"style_issues"\\s*:.*?(?="[a-z_]+"\\s*:|\\}\\s*$|\\])', "", text, flags=re.DOTALL)',
    '        text = re.sub(r\'"terminology_issues"\\s*:.*?(?="[a-z_]+"\\s*:|\\}\\s*$|\\])', "", text, flags=re.DOTALL)',
    '        text = re.sub(r\'"overall_quality"\\s*:.*?(?="[a-z_]+"\\s*:|\\}\\s*$)', "", text, flags=re.DOTALL)',
    '        text = re.sub(r\'"summary"\\s*:[^}]*(?=\\}\\s*$)', "", text, flags=re.DOTALL)',
    "",
    "        # 4. 移除描述性前缀",
    "        text = re.sub(r'^[^。，\\n]*?(?:最后输出|输出|润色后|修改后)[^:]*:', '', text, flags=re.IGNORECASE)",
    "",
    "        # 5. 如果不含 { 但有 polished_text，提取其值",
    '        if "\\"polished_text\\"" in text and not text.strip().startswith("{"):',
    '            match = re.search(r"\\"polished_text\\"\\s*:\\s*\\"(.+?)\\"(?:\\s*,|\\s*\\})", text, re.DOTALL)',
    "            if match:",
    "                text = match.group(1)",
    "",
    "        # 6. 清理多余空行",
    "        text = re.sub(r'\\n{3,}', '\\n\\n', text)",
    "",
    "        return text.strip()",
    ""
]

new_method = '\n'.join(lines) + '\n'

if old_method in content:
    new_content = content.replace(old_method, new_method)
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: File updated")
else:
    print("ERROR: Old method not found in content")