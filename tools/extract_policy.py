import os

with open('docs/knowledge/EDC16U34_KNOWLEDGE_BOOTSTRAP_PACK.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'MASTER PROMPT' in line and 'EDC16U34' in line:
        start_idx = i + 1
    if start_idx is not None and i > start_idx and line.strip() == ':::':
        end_idx = i
        break

if start_idx and end_idx:
    content = '# MASTER RESEARCH PROMPT & POLICY — EDC16U34 Project Knowledge Bootstrap\n\n'
    content += ''.join(lines[start_idx:end_idx])
    
    with open('docs/knowledge/RESEARCH_POLICY.md', 'w', encoding='utf-8') as out:
        out.write(content.strip() + '\n')
    with open('knowledge/RESEARCH_POLICY.md', 'w', encoding='utf-8') as out:
        out.write(content.strip() + '\n')
    print('Created RESEARCH_POLICY.md, lines:', end_idx - start_idx)
else:
    print('Could not find start/end:', start_idx, end_idx)
