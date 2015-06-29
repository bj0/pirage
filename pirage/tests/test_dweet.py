import pytest

from .. import dweet

thing = 'py.test_thing_23958'
key = 'some_secret_key'

@pytest.mark.slow
def test_dweet():
    dweet.report(thing, key, {'test':26})
    d = dweet.get_report(thing, key)

    assert d['test'] == 26

@pytest.mark.slow
def test_invalid_dweet():
    dweet.report(thing, key, {'test':28})

    with pytest.raises(dweet.InvalidDweetError):
        d = dweet.get_report(thing, 'bad-key')
