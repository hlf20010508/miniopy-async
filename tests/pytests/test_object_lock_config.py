import pytest

from minio import xml
from minio.commonconfig import COMPLIANCE, GOVERNANCE
from minio.objectlockconfig import DAYS, YEARS, ObjectLockConfig

def test_config():
    config = ObjectLockConfig(GOVERNANCE, 15, DAYS)
    xml.marshal(config)

    config = xml.unmarshal(
        ObjectLockConfig,
        """<ObjectLockConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<ObjectLockEnabled>Enabled</ObjectLockEnabled>
<Rule>
    <DefaultRetention>
        <Mode>COMPLIANCE</Mode>
        <Years>3</Years>
    </DefaultRetention>
</Rule>
</ObjectLockConfiguration>""",
    )
    xml.marshal(config)
    assert config.mode == COMPLIANCE
    assert config.duration == (3, YEARS)
