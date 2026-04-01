import os
import csv
import re
from pathlib import Path

ROOT_DIR = Path('knowledge-base')
REPORT_PATH = ROOT_DIR / 'baseline_audit_report.csv'

# Map filenames to their full paths for quick lookup
file_map = {}
for root, _, files in os.walk(ROOT_DIR):
    if '.git' in root or 'venv' in root: continue
    for f in files:
        if f.endswith('.md'):
            if f not in file_map:
                file_map[f] = []
            file_map[f].append(Path(root).relative_to(ROOT_DIR))

def resolve_new_link(base_file_path, old_link):
    # If the old link filename exists somewhere else, use that
    old_filename = Path(old_link).name
    if old_filename in file_map:
        # For simplicity, pick the first one found
        target_dir = file_map[old_filename][0]
        target_path = target_dir / old_filename
        
        # Calculate relative path from base_file_path to target_path
        base_dir = base_file_path.parent
        try:
            rel_path = os.path.relpath(ROOT_DIR / target_path, ROOT_DIR / base_dir)
            return rel_path
        except:
            return None
    return None

def heal():
    healed_count = 0
    with open(REPORT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['broken_links_count']) > 0:
                file_path = ROOT_DIR / row['file_path']
                broken_links = row['broken_links_details'].split('; ')
                
                with open(file_path, 'r', encoding='utf-8') as f_in:
                    content = f_in.read()
                
                new_content = content
                for broken in broken_links:
                    broken = broken.strip()
                    if not broken: continue
                    
                    new_link = resolve_new_link(Path(row['file_path']), broken)
                    if new_link:
                        # Escape special characters for regex
                        escaped_broken = re.escape(broken)
                        new_content = re.sub(f'\\({escaped_broken}\\)', f'({new_link})', new_content)
                        healed_count += 1
                
                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f_out:
                        f_out.write(new_content)

    print(f"Healed {healed_count} broken links across files.")

if __name__ == "__main__":
    heal()
