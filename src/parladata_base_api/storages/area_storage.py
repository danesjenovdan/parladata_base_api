from parladata_base_api.storages.utils import Storage, ParladataObject


class Area(ParladataObject):
    keys = ["name"]

    def __init__(self, name, id, is_new) -> None:
        self.id = id
        self.name = name
        self.is_new = is_new


class AreaStorage(Storage):
    def __init__(self, core_storage) -> None:
        super().__init__(core_storage)
        self.areas = {}
        self.storage = core_storage

    def load_data(self) -> None:
        for area in self.parladata_api.areas.get_all():
            self.store_area(area, is_new=False)

    def store_area(self, area, is_new) -> Area:
        temp_area = Area(
            name=area["name"],
            id=area["id"],
            is_new=is_new,
        )
        self.areas[temp_area.get_key()] = temp_area
        return temp_area

    def get_or_add_object(self, data) -> Area:
        if not self.areas:
            self.load_data()

        key = Area.get_key_from_dict(data)
        if key in self.areas.keys():
            area = self.areas[key]
        else:
            area = self.parladata_api.set_area(data)
            area = self.store_area(area, is_new=True)
        return area
