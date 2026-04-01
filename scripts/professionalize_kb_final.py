import os
import re

def professionalize_final():
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
        (re.compile(r'Jack / CEO / Phil', re.IGNORECASE), 'Executive Leadership'),
        (re.compile(r'Jack / Phil', re.IGNORECASE), 'Management'),
        (re.compile(r'Phil', re.IGNORECASE), 'Technical Lead'),
        (re.compile(r'Jack Elliott', re.IGNORECASE), 'Operations Manager'),
        (re.compile(r'Jack', re.IGNORECASE), 'Operations Manager'),
        (re.compile(r'Shelley', re.IGNORECASE), 'HR Manager'),
        (re.compile(r'Christy', re.IGNORECASE), 'Accounting Team'),
        (re.compile(r'Adam', re.IGNORECASE), 'Management'),
        (re.compile(r'Randy', re.IGNORECASE), 'Management'),
        (re.compile(r'Steve', re.IGNORECASE), 'IT Team'),
    ]

    # Exclude "Philips" (screwdriver/bit)
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
                        # Logic to avoid hitting "Philips" when searching for "Phil"
                        # Actually, pattern.sub will handle it if the pattern is just "Phil" 
                        # but it might hit "Philips".
                        # Let's use word boundaries \b for better precision.
                        pass

                    # Refined approach with word boundaries for short names
                    refined_replacements = [
                        (re.compile(r'\bPhil\b', re.IGNORECASE), 'Technical Lead'),
                        (re.compile(r'\bJack\b', re.IGNORECASE), 'Operations Manager'),
                        (re.compile(r'\bKathy\b', re.IGNORECASE), 'Accounting'),
                        (re.compile(r'\bBrigid\b', re.IGNORECASE), 'CEO'),
                        (re.compile(r'\bChristy\b', re.IGNORECASE), 'Accounting Team'),
                        (re.compile(r'\bPramod\b', re.IGNORECASE), 'Engineering Team'),
                        (re.compile(r'\bFinney\b', re.IGNORECASE), 'Support Lead'),
                        (re.compile(r'\bDaniel\b', re.IGNORECASE), 'Sales'),
                        (re.compile(r'\bShelley\b', re.IGNORECASE), 'HR Manager'),
                        (re.compile(r'\bAdam\b', re.IGNORECASE), 'Management'),
                        (re.compile(r'\bRandy\b', re.IGNORECASE), 'Management'),
                        (re.compile(r'\bSteve\b', re.IGNORECASE), 'IT Team'),
                    ]
                    
                    # Apply specific multi-word patterns first
                    for pattern, replacement in replacements:
                        if len(pattern.pattern) > 10: # Long patterns first
                             new_content = pattern.sub(replacement.replace('\\', '\\\\'), new_content)

                    # Apply word-boundary patterns for short names
                    for pattern, replacement in refined_replacements:
                        new_content = pattern.sub(replacement, new_content)
                    
                    if new_content != content:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Professionalized: {path}")
                except Exception as e:
                    print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    professionalize_final()
