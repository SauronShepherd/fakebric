from fakebric.redaction import redact_sensitive


def test_diagnostics_redact_common_secret_forms():
    message='Authorization: Bearer abc123 token=xyz password=hunter2 api_key=key-value'
    safe=redact_sensitive(message)
    assert 'abc123' not in safe and 'xyz' not in safe and 'hunter2' not in safe and 'key-value' not in safe
    assert safe.count('[REDACTED]')==4
    structured=redact_sensitive('{"token":"abc","password":"def"}')
    assert 'abc' not in structured and 'def' not in structured
