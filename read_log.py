try:
    with open('migration_error.log', 'r', encoding='utf-16') as f:
        lines = f.readlines()
except UnicodeError:
    with open('migration_error.log', 'r', encoding='utf-8') as f:
        lines = f.readlines()

for i, line in enumerate(lines):
    print(f"Line {i}: {line}")
