import os
import csv
import re
from pathlib import Path

ROOT_DIR = Path('knowledge-base')
REPORT_PATH = ROOT_DIR / 'baseline_audit_report.csv'

def cleanup():
    cleaned_count = 0
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
                    
                    # Find all links to this broken path and replace with text + (TBD)
                    # We need to find the text part: [Link Text](broken/path)
                    escaped_broken = re.escape(broken)
                    # Regex to find [text](broken)
                    pattern = f'\\[(.*?)\\]\\({escaped_broken}\\)'
                    new_content = re.sub(pattern, r'\1 (TBD)', new_content)
                    cleaned_count += 1
                
                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f_out:
                        f_out.write(new_content)

    print(f"Cleaned up {cleaned_count} dead links.")

if __name__ == "__main__":
    cleanup()
