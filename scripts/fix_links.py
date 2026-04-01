import os
import re

def fix_links():
    # Map old link pattern to new link pattern
    # We need to handle relative paths carefully, but since we are moving from
    # customer-success/workflows/onboarding-handoff-sop.md to
    # implementation/client-onboarding/sales-to-implementation-handoff.md
    # a simple relative adjustment might not work for every file.
    # However, the audit report showed the exact strings being flagged.
    
    # Common broken link patterns found in audit
    replacements = [
        (r'../../customer-success/workflows/onboarding-handoff-sop.md', r'../../implementation/client-onboarding/sales-to-implementation-handoff.md'),
        (r'onboarding-handoff-sop.md', r'../../implementation/client-onboarding/sales-to-implementation-handoff.md'), # For files in the same dir as the old one
        (r'../../../customer-success/workflows/onboarding-handoff-sop.md', r'../../../implementation/client-onboarding/sales-to-implementation-handoff.md'),
    ]

    for root, dirs, files in os.walk('knowledge-base'):
        for file in files:
            if file.endswith('.md'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                for old, new in replacements:
                    # Determine correct relative path if possible, but let's try the direct ones first
                    new_content = new_content.replace(old, new)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed links in: {path}")

if __name__ == "__main__":
    fix_links()
