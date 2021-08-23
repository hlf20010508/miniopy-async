from minio import xml
from minio.commonconfig import Tags
from minio.tagging import Tagging

def test_tagging():
    tags = Tags()
    tags["Project"] = "Project One"
    tags["User"] = "jsmith"
    tagging = Tagging(tags)
    xml.marshal(tagging)

    config = xml.unmarshal(
        Tagging,
        """<Tagging xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<TagSet>
<Tag>
    <Key>key1</Key>
    <Value>value1</Value>
</Tag>
<Tag>
    <Key>key2</Key>
    <Value>value2</Value>
</Tag>
</TagSet>
</Tagging>""",
    )
    xml.marshal(config)
