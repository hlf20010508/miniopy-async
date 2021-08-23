import pytest

from minio import xml
from minio.legalhold import LegalHold

def test_legal_hold_status():
    config = LegalHold(True)
    xml.marshal(config)

    config = xml.unmarshal(
        LegalHold,
        """<LegalHold xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
        <Status>OFF</Status>
        </LegalHold>""",
    )
    xml.marshal(config)
    assert config.status == False