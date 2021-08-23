import pytest

from minio import xml
from minio.commonconfig import DISABLED, ENABLED, AndOperator, Filter, Tags
from minio.replicationconfig import (DeleteMarkerReplication, Destination,
                                     ReplicationConfig, Rule)

def test_replication_config():
    tags = Tags()
    tags.update({"key1": "value1", "key2": "value2"})
    config = ReplicationConfig(
        "REPLACE-WITH-ACTUAL-ROLE",
        [
            Rule(
                Destination(
                    "REPLACE-WITH-ACTUAL-DESTINATION-BUCKET-ARN",
                ),
                ENABLED,
                delete_marker_replication=DeleteMarkerReplication(
                    DISABLED,
                ),
                rule_filter=Filter(AndOperator("TaxDocs", tags)),
                rule_id="rule1",
                priority=1,
            ),
        ],
    )
    xml.marshal(config)

    config = xml.unmarshal(
        ReplicationConfig,
        """<ReplicationConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Role>arn:aws:iam::35667example:role/CrossRegionReplicationRoleForS3</Role>
<Rule>
<ID>rule1</ID>
<Status>Enabled</Status>
<Priority>1</Priority>
<DeleteMarkerReplication>
    <Status>Disabled</Status>
</DeleteMarkerReplication>
<Filter>
    <And>
        <Prefix>TaxDocs</Prefix>
        <Tag>
            <Key>key1</Key>
            <Value>value1</Value>
        </Tag>
        <Tag>
            <Key>key1</Key>
            <Value>value1</Value>
        </Tag>
    </And>
</Filter>
<Destination>
    <Bucket>arn:aws:s3:::exampletargetbucket</Bucket>
</Destination>
</Rule>
</ReplicationConfiguration>""",
    )
    xml.marshal(config)
