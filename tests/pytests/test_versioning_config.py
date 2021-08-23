from minio import xml
from minio.commonconfig import DISABLED, ENABLED
from minio.versioningconfig import OFF, SUSPENDED, VersioningConfig

def test_versioning_config():
    config = VersioningConfig(ENABLED)
    xml.marshal(config)

    config = xml.unmarshal(
        VersioningConfig,
        """<VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
</VersioningConfiguration>""",
    )
    xml.marshal(config)
    assert config.status == OFF

    config = xml.unmarshal(
        VersioningConfig,
        """<VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Status>Enabled</Status>
</VersioningConfiguration>""",
    )
    xml.marshal(config)
    assert config.status == ENABLED

    config = xml.unmarshal(
        VersioningConfig,
        """<VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Status>Suspended</Status>
<MFADelete>Disabled</MFADelete>
</VersioningConfiguration>""",
    )
    xml.marshal(config)
    assert config.status == SUSPENDED
    assert config.mfa_delete == DISABLED
