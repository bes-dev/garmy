#!/usr/bin/env python3
"""Fix with syntax for Python 3.8 compatibility."""

import glob
import re

def fix_with_syntax(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    changed = False
    
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('with ('):
            # Found parenthesized with statement
            changed = True
            # Start with 'with ' instead of 'with ('
            new_lines.append(line.replace('with (', 'with '))
            i += 1
            
            # Collect context managers until we find the closing )
            context_managers = []
            while i < len(lines) and not ('):' in lines[i]):
                cm_line = lines[i].strip()
                if cm_line and not cm_line.startswith(')'):
                    context_managers.append(cm_line)
                i += 1
            
            # Process the closing line
            if i < len(lines) and '):' in lines[i]:
                closing_line = lines[i].strip()
                if closing_line != '):':
                    # There's content before ):
                    content_before_close = closing_line.replace('):', '').strip()
                    if content_before_close:
                        context_managers.append(content_before_close)
            
            # Add context managers with backslash continuation
            for j, cm in enumerate(context_managers):
                cm = cm.rstrip(',')  # Remove trailing comma
                if j < len(context_managers) - 1:
                    new_lines.append(f'     {cm}, \\\n')
                else:
                    new_lines.append(f'     {cm}:\n')
        else:
            new_lines.append(line)
        i += 1
    
    if changed:
        with open(filename, 'w') as f:
            f.writelines(new_lines)
        return True
    return False

# Process all test files except MCP ones
for filename in glob.glob('tests/test_*.py'):
    if 'test_mcp' not in filename:
        if fix_with_syntax(filename):
            print(f'Fixed {filename}')