import os
import re

def professionalize():
    replacements = [
        (re.compile(r'Kathy \(Bookkeeper\)', re.IGNORECASE), 'Bookkeeper'),
        (re.compile(r'Bookkeeper \(Kathy\)', re.IGNORECASE), 'Bookkeeper'),
        (re.compile(r'Controller \(Kathy\)', re.IGNORECASE), 'Controller'),
        (re.compile(r'Kathy \(Controller\)', re.IGNORECASE), 'Controller'),
        (re.compile(r'CEO \(Brigid\)', re.IGNORECASE), 'CEO'),
        (re.compile(r'Brigid \(CEO\)', re.IGNORECASE), 'CEO'),
        (re.compile(r'Accounting \(Christy Kwan or Kathy Zimmerman\)', re.IGNORECASE), 'the Accounting Team'),
        (re.compile(r'Christy Kwan or Kathy Zimmerman', re.IGNORECASE), 'the Accounting Team'),
        (re.compile(r'Pramod Vaity', re.IGNORECASE), 'the Engineering Team'),
        (re.compile(r'Pramod', re.IGNORECASE), 'the Engineering Team'),
        (re.compile(r'Row and his team', re.IGNORECASE), 'The Operations Team'),
        (re.compile(r'Finney', re.IGNORECASE), 'the Support Lead'),
        (re.compile(r'O:\\Kathy - Accounting', re.IGNORECASE), r'O:\\Accounting'),
        (re.compile(r'Kathy', re.IGNORECASE), 'Accounting'),
        (re.compile(r'ask Jack for source file', re.IGNORECASE), 'refer to the internal document repository for the source file'),
        (re.compile(r'ask Jack', re.IGNORECASE), 'refer to the internal document repository'),
        (re.compile(r'Phil Taylor', re.IGNORECASE), 'Technical Lead'),
        (re.compile(r'Daniel Almodovar', re.IGNORECASE), 'Sales Representative'),
        (re.compile(r'Daniel\'s', re.IGNORECASE), 'The Sales Team\'s'),
        (re.compile(r'Daniel', re.IGNORECASE), 'Sales'),
        (re.compile(r'Brigid', re.IGNORECASE), 'CEO'),
        (re.compile(r'Jack / Phil / Brigid', re.IGNORECASE), 'Executive Leadership'),
        (re.compile(r'Jack / Phil', re.IGNORECASE), 'Management'),
    ]

    # Exclude "Philips" (screwdriver)
    philips_safe = re.compile(r'Philips', re.IGNORECASE)

    for root, dirs, files in os.walk('knowledge-base'):
        for file in files:
            if file.endswith('.md') or file.endswith('.csv'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    for pattern, replacement in replacements:
                        # Special check for Philips vs Phil
                        if pattern.pattern == 'Phil' and philips_safe.search(content):
                            # This is a bit complex for a simple script, 
                            # but let's assume 'Phil Taylor' and 'Jack / Phil' 
                            # are handled by more specific patterns first.
                            pass
                        
                        new_content = pattern.sub(replacement.replace('\\', '\\\\'), new_content)
                    
                    if new_content != content:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Professionalized: {path}")
                except Exception as e:
                    print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    professionalize()
