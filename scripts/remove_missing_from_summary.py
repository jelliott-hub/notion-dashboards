
SUMMARY_PATH = 'knowledge-base/SUMMARY.md'
MISSING_FILES_PATH = 'missing_files.txt'

def remove_missing():
    with open(SUMMARY_PATH, 'r', encoding='utf-8') as f:
        summary_lines = f.readlines()

    with open(MISSING_FILES_PATH, 'r', encoding='utf-8') as f:
        missing_files = [line.strip() for line in f if line.strip()]

    new_summary_lines = []
    removed_count = 0
    
    for line in summary_lines:
        keep = True
        for missing in missing_files:
            if f"({missing})" in line:
                keep = False
                removed_count += 1
                break
        if keep:
            new_summary_lines.append(line)

    with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
        f.writelines(new_summary_lines)

    print(f"Removed {removed_count} missing files from SUMMARY.md")

if __name__ == "__main__":
    remove_missing()
