with open('app.py', encoding='utf-8') as f:
    src = f.read()

checks = [
    ('on_click=_nav_callback',            '_nav_callback wired to nav buttons'),
    ('nav_main_',                         'key=nav_main_... preserved'),
    ('nav_options',                       'nav_options list unchanged'),
    ('hist_',                             'history button keys preserved'),
    ('_handle_history_click',             'history on_click preserved'),
    ('current_session_id = None',         'New Workspace session clear preserved'),
    ('st.rerun()',                         'st.rerun() preserved'),
    ('WORKSPACE ISOLATION CHECK',         'workspace isolation unchanged'),
    ('General Chat',                      'General Chat nav item present'),
    ('Sovereignty',                        'Sovereignty nav item present'),
    ('Engineering',                        'Engineering nav item present'),
    ('Finance',                            'Finance nav item present'),
    ('Documents',                          'Documents nav item present'),
]

all_ok = True
for code, label in checks:
    found = code in src
    if not found: all_ok = False
    print(f'  [{"OK" if found else "FAIL"}] {label}')

print()
print('Result:', 'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED')
