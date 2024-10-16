from parladata_base_api.storages.utils import ParladataObject, Storage


class AgendaItem(ParladataObject):
    key = ["name", "session"]

    def __init__(self, name, id, datetime, session, is_new) -> None:
        self.id = id
        self.name = name
        self.session = session
        self.datetime = datetime
        self.is_new = is_new

    def set_link(self, url, name):
        self.parladata_api.links.set({"url": url, "name": name, "agenda_item": self.id})


class AgendaItemStorage(Storage):
    def __init__(self, core_storage, session) -> None:
        super().__init__(core_storage)
        self.agenda_items = {}
        self.session = session

    def load_data(self) -> None:
        for agenda_item in self.parladata_api.agenda_items.get_all(
            session=self.session.id
        ):
            self.store_object(agenda_item, is_new=False)

    def store_object(self, agenda_item, is_new) -> AgendaItem:
        temp_agenda_item = AgendaItem(
            name=agenda_item["name"],
            datetime=agenda_item["datetime"],
            id=agenda_item["id"],
            session=self.session,
            is_new=is_new,
        )
        self.agenda_items[temp_agenda_item.get_key()] = temp_agenda_item
        return temp_agenda_item

    def get_or_add_object(self, data) -> AgendaItem:
        if not self.agenda_items:
            self.load_data()

        key = AgendaItem.get_key_from_dict(data)
        if key in self.agenda_items.keys():
            agenda_item = self.agenda_items[key]
        else:
            added_agenda_item = self.parladata_api.agenda_items.set(data)
            agenda_item = self.store_object(added_agenda_item, is_new=True)
        return agenda_item
