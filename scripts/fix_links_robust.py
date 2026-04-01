import os

def fix_links_robust():
    # We want to replace any link that points to onboarding-handoff-sop.md 
    # with the correct new path: implementation/client-onboarding/sales-to-implementation-handoff.md
    
    replacements = [
        ("../../customer-success/workflows/onboarding-handoff-sop.md", "../../implementation/client-onboarding/sales-to-implementation-handoff.md"),
        ("../customer-success/workflows/onboarding-handoff-sop.md", "../implementation/client-onboarding/sales-to-implementation-handoff.md"),
        ("../../../customer-success/workflows/onboarding-handoff-sop.md", "../../../implementation/client-onboarding/sales-to-implementation-handoff.md"),
        ("customer-success/workflows/onboarding-handoff-sop.md", "implementation/client-onboarding/sales-to-implementation-handoff.md"),
    ]

    for root, dirs, files in os.walk('knowledge-base'):
        for file in files:
            if file.endswith('.md'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                # Also try a regex for any path ending in onboarding-handoff-sop.md
                # But let's be safe with specific replacements first.
                for old, new in replacements:
                    new_content = new_content.replace(old, new)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed links in: {path}")

if __name__ == "__main__":
    fix_links_robust()
