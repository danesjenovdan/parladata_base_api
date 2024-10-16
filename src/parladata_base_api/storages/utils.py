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

    def get_object_by_parsername(self, object_type: str, name: str) -> object:
        """ """
        name = name.lower()
        for parser_names in getattr(self, object_type).keys():
            for parser_name in parser_names.split("|"):
                if name == parser_name:
                    return getattr(self, object_type)[parser_names]
        return None

    def get_object_by_parsername_compare_genitiv(
        self, object_type: str, name: str
    ) -> object:
        cutted_name = [word[:-2] for word in name.lower().split(" ")]
        for parser_names in getattr(self, object_type).keys():
            for parser_name in parser_names.split("|"):
                cutted_parser_name = [
                    word[:-2] for word in parser_name.lower().split(" ")
                ]
                if len(cutted_parser_name) != len(cutted_name):
                    continue
                result = []
                for i, parted_parser_name in enumerate(cutted_parser_name):
                    result.append(parted_parser_name in cutted_name[i])
                if result and all(result):
                    return getattr(self, object_type)[parser_names]
        return None


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
        elif isinstance(value, type(None)):
            return "None"
        else:
            return "-"

    def _parse_key(self, key: str, data: any = None) -> str:
        if isinstance(data, dict):
            value = data[key]
        else:
            value = getattr(self, key)

        return self._parse_value(value)
