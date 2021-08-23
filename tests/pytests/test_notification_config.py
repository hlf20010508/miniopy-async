import pytest


from minio import xml
from minio.notificationconfig import (NotificationConfig, PrefixFilterRule,
                                      QueueConfig)

def test_notification_config():
    config = NotificationConfig(
        queue_config_list=[
            QueueConfig(
                "QUEUE-ARN-OF-THIS-BUCKET",
                ['s3:ObjectCreated:*'],
                config_id="1",
                prefix_filter_rule=PrefixFilterRule("abc"),
            ),
        ],
    )
    xml.marshal(config)

    config = xml.unmarshal(
        NotificationConfig,
        """<NotificationConfiguration>
<CloudFunctionConfiguration>
<Id>ObjectCreatedEvents</Id>
<CloudFunction>arn:aws:lambda:us-west-2:35667example:function:CreateThumbnail</CloudFunction>
<Event>s3:ObjectCreated:*</Event>
</CloudFunctionConfiguration>
<QueueConfiguration>
    <Id>1</Id>
    <Filter>
        <S3Key>
            <FilterRule>
                <Name>prefix</Name>
                <Value>images/</Value>
            </FilterRule>
            <FilterRule>
                <Name>suffix</Name>
                <Value>.jpg</Value>
            </FilterRule>
        </S3Key>
    </Filter>
    <Queue>arn:aws:sqs:us-west-2:444455556666:s3notificationqueue</Queue>
    <Event>s3:ObjectCreated:Put</Event>
</QueueConfiguration>
</NotificationConfiguration>""",
    )
    xml.marshal(config)
