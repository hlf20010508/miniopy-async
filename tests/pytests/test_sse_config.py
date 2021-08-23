from minio import xml
from minio.sseconfig import AWS_KMS, Rule, SSEConfig

def test_config():
    config = SSEConfig(Rule.new_sse_s3_rule())
    xml.marshal(config)

    config = xml.unmarshal(
        SSEConfig,
        """<ServerSideEncryptionConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Rule>
<ApplyServerSideEncryptionByDefault>
    <SSEAlgorithm>aws:kms</SSEAlgorithm>
    <KMSMasterKeyID>arn:aws:kms:us-east-1:1234/5678example</KMSMasterKeyID>
</ApplyServerSideEncryptionByDefault>
</Rule>
</ServerSideEncryptionConfiguration>
    """,
    )
    xml.marshal(config)
    assert config.rule.sse_algorithm == AWS_KMS
    assert config.rule.kms_master_key_id == "arn:aws:kms:us-east-1:1234/5678example"
