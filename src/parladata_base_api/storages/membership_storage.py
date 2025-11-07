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

    def set_end_time(self, end_time) -> None:
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
            self.active_voters[membership["member"]][membership["organization"]][
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
            logger.debug(f"loaded was {len(self.memberships)} memberships")

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

    def get_id_if_membership_is_parsed(self, membership) -> Membership | None:
        key = Membership.get_key_from_dict(membership)
        if key in self.memberships.keys():
            return self.memberships[key][0]
        return None

    def get_membership_in_organization(self, person, organization_id) -> Membership | None:
        for membership in person.active_memberships:
            if membership.organization.id == organization_id:
                return membership
        return None

    def refresh_per_person_memberships(self) -> None:
        """ """
        self.keep_membership_ids = []
        memberships_to_end = []

        for person_memberships in self.temporary_data.values():
            print(person_memberships)
            party_membership = person_memberships.get("party", None)
            if party_membership:
                party_membership = party_membership[0]
                self.membership_processing(party_membership, is_party_membership=True)

            for membership in person_memberships.get("committee", []):
                self.membership_processing(membership, is_party_membership=False)

                # membership["on_behalf_of"] = party["organization"]
                # self.membership_storage.temporary_data[
                #     membership["organization"].id
                # ].append(membership)

    def membership_processing(
        self,
        single_org_membership,
        is_party_membership: bool = False,
    ) -> None:
        if membership := self.get_id_if_membership_is_parsed(single_org_membership):
            self.keep_membership_ids.append(membership.id)
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
            existing_party_memberships = self.get_membership_in_organization(
                member, on_behalf_of.id
            )
            if existing_party_memberships:
                if existing_party_memberships.role != role:
                    # if user changed party role
                    existing_party_memberships.set_end_time(self.end_time)
                    need_to_add_voter_membership = False

        # Create party membership if on_behalf_of exists
        if on_behalf_of:
            if is_party_membership:
                # This is a party membership - create membership in the party
                org_id = on_behalf_of.id
            else:
                # This is a committee membership - create membership in the committee
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
            self.keep_membership_ids.append(stored_membership.id)
        # Note: If on_behalf_of is None (independent member), no party membership is created

        # Create voter membership if needed
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
            self.keep_membership_ids.append(stored_membership.id)
            if stored_membership.is_new:
                self.fix_user_membership(member, organization.id, on_behalf_of)

    def end_old_memberships_after_parsing(self) -> None:
        """
        End memberships that are no longer valid after parsing new data.
        This method should be called after refresh_per_person_memberships.
        
        Checks for active voter memberships that weren't parsed (not in keep_membership_ids)
        and removes both the voter membership and associated party membership.
        
        Works for all organizations (main org, working bodies, etc.) and handles 
        independent members (on_behalf_of=None) correctly.
        """
        memberships_to_end = []
        
        # Find all voter memberships that weren't parsed
        for person_id, orgs in self.active_voters.items():
            for org_id, on_behalf_orgs in orgs.items():
                for on_behalf_id, memberships in on_behalf_orgs.items():
                    for membership in memberships:
                        if membership.id not in self.keep_membership_ids and membership.role == "voter":
                            logger.debug(f"Found unparsed voter membership: person={person_id}, org={org_id}, on_behalf_of={on_behalf_id}")
                            memberships_to_end.append(membership)
        
        # End the voter memberships and their associated party memberships
        for voter_membership in memberships_to_end:
            logger.debug(f"Ending voter membership {voter_membership.id} for person {voter_membership.member.id}")
            
            # End the voter membership
            voter_membership.set_end_time(self.end_time)
            
            # Remove from person's active memberships
            if voter_membership.member and hasattr(voter_membership.member, "active_memberships"):
                try:
                    voter_membership.member.active_memberships.remove(voter_membership)
                except ValueError:
                    pass  # Already removed
            
            # Find and end associated party membership (only if on_behalf_of exists)
            if voter_membership.on_behalf_of:
                party_membership = self.get_membership_in_organization(
                    voter_membership.member, voter_membership.on_behalf_of.id
                )
                if party_membership and party_membership.role in ["member", "president", "deputy"]:
                    logger.debug(f"Ending party membership {party_membership.id} for person {voter_membership.member.id}")
                    party_membership.set_end_time(self.end_time)
                    if hasattr(voter_membership.member, "active_memberships"):
                        try:
                            voter_membership.member.active_memberships.remove(party_membership)
                        except ValueError:
                            pass  # Already removed
            else:
                logger.debug(f"Independent member {voter_membership.member.id} - no party membership to end")

    def fix_user_membership(self, person, organization_id, on_behalf_of) -> None:
        """
        This method is used to end old membership if person changed club
        and has more than one membership in the same organization (main org / commitee)

        :param person: Person object
        :param organization_id: Organization id
        :param on_behalf_of: Organization object
        """
        print("FIX USER MEMBERSHIP", person, organization_id, on_behalf_of)
        all_person_voter_orgs_dict = self.active_voters.get(person.id)
        person_voter_org_dict = all_person_voter_orgs_dict.get(organization_id, None)
        if person_voter_org_dict is None:
            # Person has no voter membership. Maybe it's a new person
            return
        if person_voter_org_dict and len(person_voter_org_dict) > 1:
            # person has change a club
            for org_id, org_memberships in person_voter_org_dict.items():
                if org_id != (on_behalf_of.id if on_behalf_of else None):
                    for m in org_memberships:
                        m.set_end_time(self.end_time)
                        try:
                            m.member.active_memberships.remove(m)
                        except ValueError:
                            pass  # Already removed
                        if organization_id == self.storage.main_org_id:
                            # Create a copy to avoid modification during iteration
                            active_memberships_copy = m.member.active_memberships.copy()
                            for pm in active_memberships_copy:
                                if pm.organization == m.on_behalf_of and pm.role in [
                                    "member",
                                    "president",
                                    "deputy",
                                ]:
                                    pm.set_end_time(self.end_time)
                                    try:
                                        pm.member.active_memberships.remove(pm)
                                    except ValueError:
                                        pass  # Already removed

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
