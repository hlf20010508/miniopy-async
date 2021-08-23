import pytest

from minio import xml
from minio.commonconfig import ENABLED, Filter
from minio.lifecycleconfig import Expiration, LifecycleConfig, Rule, Transition


def test_life_cycle_config():
    config = LifecycleConfig(
        [
            Rule(
                ENABLED,
                rule_filter=Filter(prefix="documents/"),
                rule_id="rule1",
                transition=Transition(days=30, storage_class="GLACIER"),
            ),
            Rule(
                ENABLED,
                rule_filter=Filter(prefix="logs/"),
                rule_id="rule2",
                expiration=Expiration(days=365),
            ),
        ],
    )
    xml.marshal(config)

    config = LifecycleConfig(
        [
            Rule(
                ENABLED,
                rule_filter=Filter(prefix=""),
                rule_id="rule",
                expiration=Expiration(days=365),
            ),
        ],
    )
    xml.marshal(config)

    config = xml.unmarshal(
        LifecycleConfig,
        """<LifeCycleConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
            <Rule>
            <ID>DeleteAfterBecomingNonCurrent</ID>
            <Filter>
                <Prefix>logs/</Prefix>
            </Filter>
            <Status>Enabled</Status>
            <NoncurrentVersionExpiration>
                <NoncurrentDays>100</NoncurrentDays>
            </NoncurrentVersionExpiration>
            </Rule>
            <Rule>
            <ID>TransitionAfterBecomingNonCurrent</ID>
            <Filter>
                <Prefix>documents/</Prefix>
            </Filter>
            <Status>Enabled</Status>
            <NoncurrentVersionTransition>
                <NoncurrentDays>30</NoncurrentDays>
                <StorageClass>GLACIER</StorageClass>
            </NoncurrentVersionTransition>
            </Rule>
            </LifeCycleConfiguration>""",
    )
    xml.marshal(config)

    config = xml.unmarshal(
        LifecycleConfig,
        """<LifeCycleConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
            <Rule>
            <ID>DeleteAfterBecomingNonCurrent</ID>
            <Filter>
                <Prefix></Prefix>
            </Filter>
            <Status>Enabled</Status>
            <NoncurrentVersionExpiration>
                <NoncurrentDays>100</NoncurrentDays>
            </NoncurrentVersionExpiration>
            </Rule>
           </LifeCycleConfiguration>""",
    )
    xml.marshal(config)
