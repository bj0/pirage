from unittest.mock import MagicMock

import pytest
from unittest import mock

from pirage.app import app


@pytest.mark.asyncio
async def test_notify_called_on_change():
    with mock.patch('pirage.app.app.gcm') as gcm:
        mock_app = MagicMock(name='app')
        g = MagicMock()
        last = False

        def getitem(name):
            if name == 'garage':
                return g
            elif name == 'last_push':
                return last
            else:
                return MagicMock()

        mock_app.__getitem__.side_effect = getitem

        mock_app['garage'].door_open = False
        await app.gen_data(mock_app)
        assert not gcm.report.called

        mock_app['garage'].door_open = True
        await app.gen_data(mock_app)
        assert gcm.report.called
