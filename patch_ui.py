import os

def replace_in_file(filepath, old_str, new_str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_str not in content:
        print(f"Warning: could not find old_str in {filepath}")
    content = content.replace(old_str, new_str)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# style.css auth-form changes
replace_in_file('static/css/style.css',
'''.auth-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}''',
'''.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}''')

replace_in_file('static/css/style.css',
'''.auth-actions {
  display: flex;
  align-items: end;
  gap: 10px;
  grid-column: 1 / -1;
}''',
'''.auth-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}
.auth-actions button {
  width: 100%;
  padding: 12px 24px;
}''')

replace_in_file('static/css/style.css',
'''.user-profile-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-top: 20px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  width: fit-content;
  margin-left: auto;
  margin-right: auto;
}''',
'''.user-profile-bar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
  padding: 8px 16px 8px 20px;
  background: linear-gradient(180deg, rgba(22, 27, 34, 0.6) 0%, rgba(15, 20, 27, 0.8) 100%);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(8px);
}''')

replace_in_file('static/css/style.css',
'''.small-btn {
  padding: 4px 12px;
  font-size: 0.85rem;
  margin-bottom: 0;
  min-height: auto;
}''',
'''.small-btn {
  padding: 6px 14px;
  font-size: 0.85rem;
  margin-bottom: 0;
  min-height: auto;
  border-radius: 999px;
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
}
.small-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}''')

print("Patch applied.")
