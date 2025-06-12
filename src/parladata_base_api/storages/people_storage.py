import re

from parladata_base_api.storages.utils import ParladataObject, Storage


class Person(ParladataObject):
    keys = ["parser_names"]

    def __init__(
        self, name: str, id: int, parser_names: str, is_new: bool, parladata_api
    ) -> None:
        self.id = id
        self.name = name
        self.parser_names = parser_names
        self.is_new = is_new
        self.active_memberships = []
        self.parladata_api = parladata_api

    def save_image(self, image_url: str) -> None:
        self.parladata_api.people.upload_image(self.id, image_url)

    def add_parser_name(self, parser_name: str) -> None:
        data = self.parladata_api.people.add_person_parser_name(self.id, parser_name)
        self.parser_names = data["parser_names"]

    def __repr__(self):
        return f"<Person {self.name} [{self.id}]>"


class PeopleStorage(Storage):
    def __init__(self, core_storage) -> None:
        super().__init__(core_storage)
        self.people = {}
        self.people_by_id = {}
        self.storage = core_storage

    def load_data(self) -> None:
        for person in self.parladata_api.people.get_all():
            self.store_object(person, is_new=False)

    def store_object(self, person: dict, is_new: bool) -> Person:
        temp_person = Person(
            name=person["name"],
            parser_names=person["parser_names"],
            id=person["id"],
            is_new=is_new,
            parladata_api=self.parladata_api,
        )
        self.people[temp_person.get_key()] = temp_person
        self.people_by_id[person["id"]] = temp_person
        return temp_person

    # def get_object_by_parsername(self, name: str) -> Person:
    #     if not self.people:
    #         self.load_data()
    #     try:
    #         name = name.lower()
    #     except:
    #         return None
    #     for parser_names in self.people.keys():
    #         for parser_name in parser_names.split("|"):
    #             if name == parser_name:
    #                 return self.people[parser_names]
    #     return None

    # def get_object_by_parsername_compare_rodilnik(self, object_type, name):
    #     """
    #     """
    #     cutted_name = [word[:-2] for word in name.lower().split(' ')]
    #     for parser_names in self.people.keys():
    #         for parser_name in parser_names.split('|'):
    #             cutted_parser_name = [word[:-2] for word in parser_name.lower().split(' ')]
    #             if len(cutted_parser_name) != len(cutted_name):
    #                 continue
    #             result = []
    #             for i, parted_parser_name in enumerate(cutted_parser_name):
    #                 result.append( parted_parser_name in cutted_name[i] )
    #             if result and all(result):
    #                 return getattr(self, object_type)[parser_names]
    #     return None

    def get_or_add_object(
        self, person_data: dict, add: bool = True, name_type: str = "normal"
    ) -> Person:
        if not self.people:
            self.load_data()
        name = person_data["name"]
        prefix, name = self.get_prefix(name)
        if name_type == "genitive":
            person = self.get_object_by_parsername_compare_genitiv("people", name)
        else:
            person = self.get_object_by_parsername("people", name)
        if person:
            return person
        elif not add:
            return None
        person_data.update({"name": name.strip().title(), "parser_names": name.strip()})
        if prefix:
            person_data["honorific_prefix"] = prefix
        response_data = self.parladata_api.people.set(person_data)
        return self.store_object(response_data, is_new=True)

    def add_person_parser_name(self, person: Person, parser_name: str) -> Person:
        updated_person = self.parladata_api.people.add_person_parser_name(
            person.id, parser_name
        )
        new_person = self.store_object(updated_person)
        del self.people[person.parser_name.lower()]
        return new_person

    def get_person_by_id(self, id: int) -> Person:
        if not self.people:
            self.load_data()
        return self.people_by_id.get(id, None)

    def get_prefix(self, name: str) -> tuple:
        prefix = re.findall("^[a-z]{0,4}\.", name)
        if prefix:
            prefix = prefix[0]
            return prefix, name.replace(prefix, "").strip().title()
        else:
            return None, name
