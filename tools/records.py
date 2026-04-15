import client


def query_records(soql: str) -> list[dict]:
    sf = client.get_client()
    result = sf.query_all(soql)
    return result["records"]


def get_record(object_name: str, record_id: str) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    return dict(obj.get(record_id))


def create_record(object_name: str, fields: dict) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    return obj.create(fields)


def update_record(object_name: str, record_id: str, fields: dict) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    result = obj.update(record_id, fields)
    return {"status_code": result}


def delete_record(object_name: str, record_id: str) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    result = obj.delete(record_id)
    return {"status_code": result}
