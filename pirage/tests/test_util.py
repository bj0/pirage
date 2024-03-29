from pirage.util import shelf, tempdir


def test_shelf():
    import os
    import glob

    with tempdir() as path:
        with shelf(os.path.join(path, 'test.db')) as s:
            s['test'] = {'a test': 25}

        assert len(glob.glob(os.path.join(path, 'test.db*'))) > 0

        with shelf(os.path.join(path, 'test.db')) as s:
            assert s['test']['a test'] == 25
            assert s.get('test', {}).get('a test', 0) == 25
