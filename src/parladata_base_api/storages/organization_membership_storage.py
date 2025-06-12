import logging
from collections import defaultdict
from datetime import datetime

from parladata_base_api.storages.utils import ParladataObject, Storage

logger = logging.getLogger("logger")


class OrganizationMembership(ParladataObject):
    keys = ["member", "organization", "mandate"]

    def __init__(
        self,
        member_id,
        organization_id,
        start_time,
        end_time,
        mandate,
        id,
        is_new,
        parladata_api,
    ) -> None:
        self.id = id
        self.member = member_id
        self.organization = organization_id
        self.start_time = start_time
        self.end_time = end_time
        self.mandate = mandate
        self.is_new = is_new
        self.parladata_api = parladata_api

    def set_end_time(self, end_time) -> dict:
        self.end_time = end_time
        self.parladata_api.organization_memberships.patch(
            self.id, {"end_time": end_time}
        )


class OrganizationMembershipStorage(Storage):
    def __init__(self, core_storage) -> None:
        super().__init__(core_storage)
        self.memberships = defaultdict(list)

        self.temporary_data = defaultdict(list)
        self.temporary_roles = defaultdict(list)

        self.active_voters = defaultdict(dict)

        self.first_load = False

    def store_object(self, membership, is_new) -> OrganizationMembership:
        temp_membership = OrganizationMembership(
            member_id=membership["member"],
            organization_id=membership["organization"],
            start_time=membership["start_time"],
            end_time=membership.get("end_time", None),
            mandate=membership["mandate"],
            id=membership["id"],
            is_new=is_new,
            parladata_api=self.parladata_api,
        )
        self.memberships[temp_membership.get_key()].append(temp_membership)

        return temp_membership

    def load_data(self) -> None:
        if not self.memberships:
            for membership in self.parladata_api.organizations_memberships.get_all(
                mandate=self.storage.mandate_id
            ):
                self.store_object(membership, is_new=False)
            logger.debug(f"laoded was {len(self.memberships)} memberships")

        if not self.memberships:
            self.first_load = True

    def get_or_add_object(self, data) -> OrganizationMembership:
        if not self.memberships:
            self.load_data()
        key = OrganizationMembership.get_key_from_dict(data)
        if key in self.memberships.keys():
            memberships = self.memberships[key]
            for membership in memberships:
                if not membership.end_time:
                    return membership

        membership = self.set_membership(data)
        return membership

    def set_membership(self, data) -> OrganizationMembership:
        added_membership = self.parladata_api.organization_memberships.set(data)
        new_membership = self.store_object(added_membership, is_new=True)
        return new_membership

    def check_if_membership_is_parsed(self, membership) -> bool:
        key = OrganizationMembership.get_key_from_dict(membership)
        return key in self.memberships.keys()
