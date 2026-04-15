import client


def list_objects() -> list[dict]:
    sf = client.get_client()
    result = sf.describe()
    return [
        {"name": obj["name"], "label": obj["label"]}
        for obj in result["sobjects"]
        if obj["queryable"]
    ]


def describe_object(object_name: str) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    desc = obj.describe()
    return {
        "name": desc["name"],
        "label": desc["label"],
        "fields": [
            {"name": f["name"], "label": f["label"], "type": f["type"]}
            for f in desc["fields"]
        ],
    }
