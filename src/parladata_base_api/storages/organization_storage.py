from parladata_base_api.storages.utils import ParladataObject, Storage


class Organization(ParladataObject):
    keys = ["parser_names"]

    def __init__(
        self,
        name: str,
        id: int,
        parser_names: str,
        is_new: bool,
        gov_id: str = None,
        classification: str = None,
    ) -> None:
        self.id = id
        self.name = name
        self.parser_names = parser_names
        self.gov_id = gov_id
        self.classification = classification
        self.is_new = is_new
        self.memberships = []
        self.active_memberships_by_member_id = {}

    def __repr__(self):
        return f"<Organization: {self.name} [{self.id}]>"


class OrganizationStorage(Storage):
    def __init__(self, core_storage) -> None:
        super().__init__(core_storage)
        self.organizations = {}
        self.organizations_by_id = {}
        self.organizations_by_gov_id = {}
        self.active_memberships_by_member_id = {}

    def load_data(self) -> None:
        for organization in self.parladata_api.organizations.get_all():
            if not organization["parser_names"]:
                continue
            self.store_object(organization, is_new=False)

    def store_object(self, organization: dict, is_new: bool) -> Organization:
        temp_organization = Organization(
            name=organization["name"],
            parser_names=organization["parser_names"],
            id=organization["id"],
            is_new=is_new,
            gov_id=organization.get("gov_id", None),
            classification=organization.get("classification", None),
        )
        self.organizations[temp_organization.get_key()] = temp_organization
        self.organizations_by_id[organization["id"]] = temp_organization
        if temp_organization.gov_id:
            self.organizations_by_gov_id[temp_organization.gov_id] = temp_organization
        return temp_organization

    # def get_object_by_parsername(self, name: str) -> Organization:
    #     if not self.organizations:
    #         self.load_data()
    #     try:
    #         name = name.lower()
    #     except:
    #         return None
    #     for parser_names in self.organizations.keys():
    #         for parser_name in parser_names.split("|"):
    #             if name == parser_name:
    #                 return self.organizations[parser_names]
    #     return None

    def get_or_add_object(
        self, organization_data: dict, add: bool = True
    ) -> Organization:
        if not self.organizations:
            self.load_data()
        organization = self.get_object_by_parsername(
            "organizations", organization_data["name"]
        )
        if organization:
            return organization
        elif not add:
            return None
        response_data = self.parladata_api.organizations.set(organization_data)
        return self.store_object(response_data, is_new=True)

    def get_organization_by_id(self, id: int) -> Organization:
        if not self.organizations:
            self.load_data()
        return self.organizations_by_id.get(id, None)

    def get_organization_by_gov_id(self, gov_id):
        if not self.organizations:
            self.load_data()
        return self.organizations_by_gov_id.get(gov_id, None)
