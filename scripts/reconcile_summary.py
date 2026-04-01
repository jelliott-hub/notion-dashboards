import os
from pathlib import Path

SUMMARY_PATH = 'knowledge-base/SUMMARY.md'
ORPHANS_PATH = 'orphans.txt'

def get_title_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Try to find the first H1 title
            import re
            match = re.search(r'^#\s+(.*)', content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    except:
        pass
    # Fallback to filename
    return Path(file_path).stem.replace('-', ' ').title()

def reconcile():
    with open(SUMMARY_PATH, 'r', encoding='utf-8') as f:
        summary_lines = f.readlines()

    with open(ORPHANS_PATH, 'r', encoding='utf-8') as f:
        orphans = [line.strip() for line in f if line.strip()]

    # Map directories to their position in SUMMARY.md
    dir_positions = {}
    for i, line in enumerate(summary_lines):
        import re
        match = re.search(r'\((.*?)\)', line)
        if match:
            path = match.group(1)
            parent_dir = os.path.dirname(path)
            if parent_dir not in dir_positions:
                dir_positions[parent_dir] = i

    new_orphans = []
    
    for orphan in orphans:
        if orphan in ['.gemini-context/perfectionist_v2.md', 'templates/CLAUDE.md']:
            continue # Skip system/config files

        parent_dir = os.path.dirname(orphan)
        title = get_title_from_file(os.path.join('knowledge-base', orphan))
        new_line = f"  * [{title}]({orphan})\n" # Basic indentation, might need adjustment

        # Find best insertion point
        inserted = False
        # Try to find the exact parent dir
        if parent_dir in dir_positions:
            pos = dir_positions[parent_dir]
            # Find the end of this block (next line with less or equal indentation that isn't empty)
            current_indent = len(summary_lines[pos]) - len(summary_lines[pos].lstrip())
            insert_pos = pos + 1
            while insert_pos < len(summary_lines):
                next_line = summary_lines[insert_pos]
                if next_line.strip() == "":
                    insert_pos += 1
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= current_indent and next_line.strip().startswith('*'):
                    break
                if next_line.strip().startswith('##'):
                    break
                insert_pos += 1
            
            # Adjust indentation based on previous line
            prev_line = summary_lines[insert_pos-1]
            prev_indent = len(prev_line) - len(prev_line.lstrip())
            new_line = " " * prev_indent + f"* [{title}]({orphan})\n"
            
            summary_lines.insert(insert_pos, new_line)
            # Update subsequent positions
            for d in dir_positions:
                if dir_positions[d] >= insert_pos:
                    dir_positions[d] += 1
            inserted = True
        
        if not inserted:
            new_orphans.append(orphan)

    # Append truly uncategorized orphans at the end
    if new_orphans:
        summary_lines.append("\n## ðŸ“¦ Additional Reference\n\n")
        for orphan in new_orphans:
            title = get_title_from_file(os.path.join('knowledge-base', orphan))
            summary_lines.append(f"* [{title}]({orphan})\n")

    with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
        f.writelines(summary_lines)

    print(f"Reconciled {len(orphans)} orphans into SUMMARY.md")

if __name__ == "__main__":
    reconcile()
