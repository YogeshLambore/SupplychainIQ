import ast, re

with open('app.py', encoding='utf-8') as f:
    src = f.read()

ast.parse(src)
print('app.py: OK')

# Verify nav_labels keys match nav_options
nav_options_m = re.search(r'nav_options\s*=\s*\[([^\]]+)\]', src)
nav_labels_m  = re.search(r'nav_labels\s*=\s*\{(.+?)\}', src, re.DOTALL)

options = [x.strip().strip('"').strip("'") for x in nav_options_m.group(1).split(',')]
labels  = re.findall(r'"([^"]+)":', nav_labels_m.group(1))

print(f'nav_options: {options}')
print(f'nav_labels keys: {labels}')
print('Keys match:', set(options) == set(labels))

# Verify args=(option,) — not nav_labels[option] — so routing is intact
args_ok = "args=(option,)" in src
print(f'args=(option,) preserved: {args_ok}')

# Verify key unchanged
key_ok = 'key=f"nav_main_{option}"' in src
print(f'key=nav_main_{{option}} preserved: {key_ok}')

# Verify on_click unchanged
oc_ok = 'on_click=_nav_callback' in src
print(f'on_click=_nav_callback preserved: {oc_ok}')
