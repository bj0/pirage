from unittest.mock import Mock


def assert_does_not_have_calls(self, *args, **kwargs):
    try:
        self.assert_has_calls(*args, **kwargs)
    except AssertionError:
        return
    raise AssertionError('Expected %s to not have been called.' % self._format_mock_call_signature(args, kwargs))


Mock.assert_does_not_have_calls = assert_does_not_have_calls
