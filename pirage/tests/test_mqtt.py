import pytest
import time

from .. import mqtt

@pytest.mark.slow
def test_mqtt():

    with mqtt.get_report_queue("pirage/test") as q:
        mqtt.report("pirage/test", "test_data")
        ret = q.get(timeout=5)
        assert ret == ("pirage/test","test_data")
