from datetime import datetime, timedelta, timezone

from minio import xml
from minio.commonconfig import COMPLIANCE, GOVERNANCE
from minio.retention import Retention

def test_retention():
    config = Retention(GOVERNANCE, datetime.utcnow() + timedelta(days=10))
    xml.marshal(config)

    config = xml.unmarshal(
        Retention,
        """<Retention xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Mode>COMPLIANCE</Mode>
<RetainUntilDate>2020-10-02T00:00:00Z</RetainUntilDate>
</Retention>""",
    )
    xml.marshal(config)
    assert config.mode == COMPLIANCE
    assert config.retain_until_date == datetime(2020, 10, 2, 0, 0, 0, 0, timezone.utc)
