from pathlib import Path


def test_ui_shell_exposes_stable_accessibility_contract():
    root=Path(__file__).parents[1] / 'fakebric' / 'static'
    html=(root/'index.html').read_text(encoding='utf-8')
    javascript=(root/'app.js').read_text(encoding='utf-8')
    assert 'aria-label="Workspaces"' in html and 'aria-live="polite"' in html
    assert "dataset.testid='create-workspace'" in javascript
    assert 'data-ws' in javascript and 'data-item' in javascript
