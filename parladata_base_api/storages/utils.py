class Storage(object):
    def __init__(self, core_storage) -> None:
        self.storage = core_storage
        self.parladata_api = core_storage.parladata_api

    def get_or_add_object(self, data) -> object:
        raise NotImplementedError

    def store_object(self, data) -> object:
        raise NotImplementedError

    def load_data(self) -> None:
        raise NotImplementedError


class ParladataObject(object):
    keys = ["gov_id"]

    def get_key(self) -> str:
        return "_".join([self._parse_key(k, None) for k in self.keys])

    @classmethod
    def get_key_from_dict(ctl, data) -> str:
        return "_".join([ctl._parse_key(ctl, k, data) for k in ctl.keys])

    @classmethod
    def _parse_value(ctl, value: any) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        elif isinstance(value, int):
            return str(value)
        elif isinstance(value, list):
            value.sort()
            return "-".join([ctl._parse_value(v) for v in value])
        elif isinstance(value, object):
            return str(value.id) if value else "-"
        else:
            return "-"

    def _parse_key(self, key: str, data: any = None) -> str:
        print(data)
        if isinstance(data, dict):
            value = data[key]
        else:
            print(self, key)
            value = getattr(self, key)

        print(value)
        return self._parse_value(value)
