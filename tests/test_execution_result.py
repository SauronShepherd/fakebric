from fakebric.execution_result import execution_succeeded


def test_execution_requires_machine_readable_success_record():
    assert execution_succeeded('noise\n{"status":"completed"}\n')
    assert execution_succeeded(b'{"status": "completed"}\n')
    assert not execution_succeeded('{"status":"failed"}\n')
    assert not execution_succeeded('Traceback: notebook failed\n')
