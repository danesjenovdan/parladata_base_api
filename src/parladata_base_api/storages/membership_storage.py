import logging
from collections import defaultdict
from datetime import datetime, timedelta

from parladata_base_api.storages.utils import ParladataObject, Storage

logger = logging.getLogger("logger")


class Membership(ParladataObject):
    keys = ["member", "organization", "on_behalf_of", "role", "mandate"]

    def __init__(
        self,
        person,
        organization,
        on_behalf_of,
        role,
        start_time,
        end_time,
        mandate,
        id,
        is_new,
        parladata_api,
    ) -> None:
        self.id = id
        self.member = person
        self.organization = organization
        self.on_behalf_of = on_behalf_of
        self.role = role
        self.start_time = start_time
        self.end_time = end_time
        self.mandate = mandate
        self.is_new = is_new
        self.parladata_api = parladata_api

    def set_end_time(self, end_time) -> dict:
        self.end_time = end_time
        self.parladata_api.person_memberships.patch(self.id, {"end_time": end_time})


class MembershipStorage(Storage):
    def __init__(self, core_storage) -> None:
        super().__init__(core_storage)
        self.memberships = defaultdict(list)

        self.temporary_data = defaultdict(list)
        self.temporary_roles = defaultdict(list)

        self.active_voters = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.first_load = False

    def store_object(self, membership, is_new) -> Membership:
        person = self.storage.people_storage.get_person_by_id(membership["member"])
        organization = self.storage.organization_storage.get_organization_by_id(
            membership["organization"]
        )
        if membership["on_behalf_of"]:
            on_behalf_of = self.storage.organization_storage.get_organization_by_id(
                membership["on_behalf_of"]
            )
        else:
            on_behalf_of = None
        temp_membership = Membership(
            person=person,
            organization=organization,
            on_behalf_of=on_behalf_of,
            role=membership["role"],
            start_time=membership["start_time"],
            end_time=membership.get("end_time", None),
            mandate=membership["mandate"],
            id=membership["id"],
            is_new=is_new,
            parladata_api=self.parladata_api,
        )
        self.memberships[temp_membership.get_key()].append(temp_membership)

        if not membership.get("end_time", None):
            organization.active_memberships_by_member_id[membership["member"]] = (
                temp_membership
            )

        if (
            membership.get("end_time", None) == None
            or membership["end_time"] > datetime.now().isoformat()
        ) and membership["role"] == "voter":
            self.active_voters[membership["organization"]][membership["member"]][
                membership["on_behalf_of"]
            ].append(temp_membership)

        if person and (not membership.get("end_time", None)):
            person.active_memberships.append(temp_membership)
        if organization:
            organization.memberships.append(temp_membership)
        return temp_membership

    def load_data(self) -> None:
        if not self.memberships:
            for membership in self.parladata_api.person_memberships.get_all(
                mandate=self.storage.mandate_id
            ):
                self.store_object(membership, is_new=False)
            logger.debug(f"laoded was {len(self.memberships)} memberships")

        if not self.memberships:
            self.first_load = True

        if self.first_load:
            self.default_start_time = self.storage.mandate_start_time.isoformat()
        else:
            self.default_start_time = datetime.now().isoformat()

    def get_or_add_object(self, data) -> Membership:
        if not self.memberships:
            self.load_data()
        key = Membership.get_key_from_dict(data)
        if key in self.memberships.keys():
            memberships = self.memberships[key]
            for membership in memberships:
                if not membership.end_time:
                    return membership

        membership = self.set_membership(data)
        return membership

    def set_membership(self, data) -> Membership:
        added_membership = self.parladata_api.person_memberships.set(data)
        new_membership = self.store_object(added_membership, is_new=True)
        return new_membership

    def get_id_if_membership_is_parsed(self, membership) -> bool:
        key = Membership.get_key_from_dict(membership)
        if key in self.memberships.keys():
            return self.memberships[key][0]
        return None

    def get_membership_in_organiaztion(self, person, organization_id) -> Membership:
        for membership in person.active_memberships:
            if membership.organization.id == organization_id:
                return membership

    def refresh_per_person_memberships(self) -> None:
        """ """
        self.keep_memebrship_ids = []
        memberships_to_end = []

        for person_memberships in self.temporary_data.values():
            print(person_memberships)
            party_membership = person_memberships.get("party", None)
            if party_membership:
                party_membership = party_membership[0]
                self.membership_proccessing(party_membership, is_party_membership=True)

            for membership in person_memberships.get("commitee", []):
                self.membership_proccessing(party_membership, is_party_membership=True)

                # membership["on_behalf_of"] = party["organization"]
                # self.membership_storage.temporary_data[
                #     membership["organization"].id
                # ].append(membership)

    def membership_proccessing(
        self,
        single_org_membership,
        is_party_membership: bool = False,
    ) -> None:
        if membership := self.get_id_if_membership_is_parsed(single_org_membership):
            self.keep_memebrship_ids.append(membership.id)
            return
        # get start&end time for the membership
        if start_time := single_org_membership.get("start_time"):
            pass
        else:
            start_time = self.default_start_time

        if end_time := single_org_membership.get("end_time"):
            pass
        else:
            end_time = (
                datetime.fromisoformat(self.default_start_time) - timedelta(seconds=1)
            ).isoformat()

        self.end_time = end_time

        need_to_add_voter_membership = single_org_membership["is_voter"]

        organization = single_org_membership["organization"]
        on_behalf_of = single_org_membership["on_behalf_of"]

        member = single_org_membership["member"]
        role = single_org_membership.get("role", "member")

        if self.temporary_roles:
            if is_party_membership:
                role = self.get_members_role_in_organization(member.id, on_behalf_of.id)
            else:
                role = self.get_members_role_in_organization(member.id, organization.id)
        logger.debug(role)

        # check if user changed party role
        if (
            organization
            and on_behalf_of
            and organization.id == self.storage.main_org_id
        ):
            existing_party_membrships = self.get_membership_in_organiaztion(
                member, on_behalf_of.id
            )
            if existing_party_membrships:
                if existing_party_membrships.role != role:
                    # if user changed party role
                    existing_party_membrships.set_end_time(self.end_time)
                    need_to_add_voter_membership = False

        if on_behalf_of:
            if is_party_membership:
                org_id = on_behalf_of.id
            else:
                org_id = organization.id
            stored_membership = self.get_or_add_object(
                {
                    "member": member.id,
                    "organization": org_id,
                    "role": role,
                    "start_time": start_time,
                    "mandate": self.storage.mandate_id,
                    "on_behalf_of": None,
                }
            )
            self.keep_memebrship_ids.append(stored_membership.id)
        else:
            if is_party_membership:
                org_id = self.storage.main_org_id

        if need_to_add_voter_membership:
            stored_membership = self.get_or_add_object(
                {
                    "member": member.id,
                    "organization": organization.id,
                    "role": "voter",
                    "start_time": start_time,
                    "mandate": self.storage.mandate_id,
                    "on_behalf_of": on_behalf_of.id if on_behalf_of else None,
                }
            )
            self.keep_memebrship_ids.append(stored_membership.id)
            if stored_membership.is_new:
                self.fix_user_membership(member, organization.id, on_behalf_of)

    def refresh_memberships(self) -> None:
        """ """
        self.keep_memebrship_ids = []
        memberships_to_end = []

        for org_id, org_data in self.temporary_data.items():
            for single_org_membership in org_data:
                # check if membership is already parsed
                if membership := self.get_id_if_membership_is_parsed(
                    single_org_membership
                ):
                    self.keep_memebrship_ids.append(membership.id)
                    continue
                # get start&end time for the membership
                if start_time := single_org_membership.get("start_time"):
                    pass
                else:
                    start_time = self.default_start_time

                if end_time := single_org_membership.get("end_time"):
                    pass
                else:
                    end_time = (
                        datetime.fromisoformat(self.default_start_time)
                        - timedelta(seconds=1)
                    ).isoformat()

                self.end_time = end_time

                need_to_add_voter_membership = single_org_membership["is_voter"]

                logger.debug(single_org_membership)
                # get organization id
                if single_org_membership["organization"]:
                    organization = single_org_membership["organization"]
                else:
                    organization = None

                member = single_org_membership["member"]
                role = single_org_membership.get("role", "member")
                if self.temporary_roles:
                    # override role if it's parserd from separate page and stored
                    # in temporary_roles
                    role = self.get_members_role_in_organization(
                        member.id, organization.id
                    )
                logger.debug(role)

                # check if user changed party role
                if organization and org_id == self.storage.main_org_id:
                    existing_party_membrships = self.get_membership_in_organiaztion(
                        member, organization.id
                    )
                    if existing_party_membrships:
                        if existing_party_membrships.role != role:
                            # if user changed party role
                            existing_party_membrships.set_end_time(self.end_time)
                            need_to_add_voter_membership = False

                if not organization:
                    # if membership is None then not add party membership
                    party_id = None

                elif organization and org_id == self.storage.main_org_id:
                    # if current memberships if in main organization then add membership
                    # to party
                    party_id = organization.id
                else:
                    # membership represent committee like membership
                    party = single_org_membership.get("on_behalf_of", None)
                    if party:
                        party_id = party.id
                    else:
                        party_id = None
                    org_id = organization.id

                if party_id:
                    stored_membership = self.get_or_add_object(
                        {
                            "member": member.id,
                            "organization": party_id,
                            "role": role,
                            "start_time": start_time,
                            "mandate": self.storage.mandate_id,
                            "on_behalf_of": None,
                        }
                    )
                    self.keep_memebrship_ids.append(stored_membership.id)

                if need_to_add_voter_membership:
                    stored_membership = self.get_or_add_object(
                        {
                            "member": member.id,
                            "organization": org_id,
                            "role": "voter",
                            "start_time": start_time,
                            "mandate": self.storage.mandate_id,
                            "on_behalf_of": party_id,
                        }
                    )
                    self.keep_memebrship_ids.append(stored_membership.id)
                    if stored_membership.is_new:
                        self.fix_user_membership(member, org_id, organization)

        logger.debug(f"changed mambership {memberships_to_end}")

    # def end_old_memberships_after_parsing(self) -> None:
    #     for org_id, voters in self.active_voters.items():
    #         for person_id, memberships in voters.items():
    #             for membership in memberships:
    #                 if membership.id not in self.keep_memebrship_ids:

    def fix_user_membership(self, person, organization_id, on_behalf_of) -> None:
        """
        This method is used to end old membership if person changed club
        and has more than one membership in the same organization (main org / commitee)

        :param person: Person object
        :param organization_id: Organization id
        :param on_behalf_of: Organization object
        """
        print("FIX USER MEMBERSHIP", person, organization_id, on_behalf_of)
        voter_org = self.active_voters.get(organization_id)
        person_voter_org_dict = voter_org.get(person.id, None)
        if person_voter_org_dict is None:
            # Person has no voter membership. Maybe it's a new person
            return
        if person_voter_org_dict and len(person_voter_org_dict) > 1:
            # person has change a club
            for org_id, org_memberships in person_voter_org_dict.items():
                if org_id != on_behalf_of:
                    for m in org_memberships:
                        m.set_end_time(self.end_time)
                        m.member.active_memberships.remove(m)
                        if organization_id == self.storage.main_org_id:
                            for pm in m.member.active_memberships:
                                if pm.organization == m.on_behalf_of and pm.role in [
                                    "member",
                                    "president",
                                    "deputy",
                                ]:
                                    pm.set_end_time(self.end_time)
                                    pm.member.active_memberships.remove(pm)

    def get_all_active_persons_memberships(self, person_id) -> list:
        return [
            membership
            for membership in self.storage.people_storage.get_person_by_id(
                person_id
            ).memberships
            if not membership.end_time
        ]

    def count_active_voter_membership(self, person_id) -> int:
        person = self.storage.people_storage.get_person_by_id(person_id)
        count = 0
        for membership in person.active_memberships:
            if (
                membership.organization == int(self.storage.main_org_id)
                and not membership.end_time
                and membership.role == "voter"
            ):
                count += 1
        return count

    def get_members_role_in_organization(self, member_id, organization) -> str:
        role = "member"
        for person_role in self.temporary_roles[organization]:
            if str(member_id) == str(person_role["member"].id):
                return person_role["role"]
        return role

    def get_members_organization_from_roles(self, member_id) -> int:
        """
        This is used for users without profiles
        """
        role = None
        for org_id, members in self.temporary_roles.items():
            for person_role in members:
                if str(member_id) == str(person_role["member"].id):
                    role = person_role["role"]
                    return org_id
        return None
