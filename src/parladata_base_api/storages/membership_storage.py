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

    def __str__(self) -> str:
        return f"<PersonMembership(id={self.id}, member={self.member.name}, organization={self.organization.name if self.organization else None}, on_behalf_of={self.on_behalf_of.name if self.on_behalf_of else None}, role={self.role}, start_time={self.start_time}, end_time={self.end_time}, mandate={self.mandate})>"


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

    def get_membership_in_organization(
        self, person, organization_id
    ) -> Membership | None:
        """
        This method is used to get active membership of a person in an organization (party or committee).
        It's mainly used to check a person's role if he/she changes it in a party or committee.
        """
        for membership in person.active_memberships:
            if membership.organization.id == organization_id:
                return membership
        return None

    def get_voter_membership_in_organization(
        self, person, organization_id
    ) -> Membership | None:
        """
        This method is used to get active membership of a person in an organization (party or committee).
        It's mainly used to check a person's role if he/she changes it in a party or committee.
        """
        for membership in person.active_memberships:
            if membership.organization.id == organization_id:
                if membership.role == "voter":
                    return membership
        return None

    def end_membership(self, membership, end_time) -> None:
        membership.set_end_time(end_time)
        if hasattr(membership.member, "active_memberships"):
            try:
                membership.member.active_memberships.remove(membership)
            except ValueError:
                pass  # Already removed
        if membership.role == "voter":
            if membership.on_behalf_of:
                on_behalf_id = membership.on_behalf_of.id
            else:
                on_behalf_id = None
            try:
                self.active_voters[membership.member.id][membership.organization.id][
                    on_behalf_id
                ].remove(membership)
            except ValueError:
                pass  # Already removed

    def get_membership_in_organization_on_behalf_of(
        self, person, organization_id, on_behalf_of_id, exclude_role=None
    ) -> Membership | None:
        """
        This method is used to get active membership of a person in an organization (party or committee) on behalf of another organization.
        It's mainly used to check a person's role if he/she changes it in a party or committee.
        """
        for membership in person.active_memberships:
            if membership.organization.id == organization_id:
                if membership.on_behalf_of == on_behalf_of_id:
                    if exclude_role and membership.role == exclude_role:
                        continue
                    return membership
        return None

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

    def refresh_per_person_memberships(
        self, per_person_data, house_organization
    ) -> None:
        """
        This method is used to refresh memberships in parladata based on the new data from the parser.
        per_person_data is datastructure with all parserd memebrships for eeach person and type (party and committee).
        typ = "party" or "committee"
        per_person_data[person.id][typ] = [membership1, membership2, ...]
        """
        self.keep_membership_ids = []
        memberships_to_end = []
        self.load_data()

        # Fix party memberships with house organization and committee memberships with party group as on_behalf_of
        for person_memberships in per_person_data.values():
            party = person_memberships.get("party", None)
            if party:
                if isinstance(party, list):
                    party = party[0]
                party["on_behalf_of"] = party["organization"]
                party["organization"] = house_organization

            for membership in person_memberships.get("committee", []):
                membership["on_behalf_of"] = party["on_behalf_of"]

        # Process and update party and committee mamberships for each person.
        for person_memberships in per_person_data.values():
            print(person_memberships)
            party_membership = person_memberships.get("party", None)
            if party_membership:
                party_membership = party_membership[0]
                self.party_membership_processing(party_membership)

            for committee_membership in person_memberships.get("committee", []):
                self.committee_membership_processing(committee_membership)

        # Detete memberships which are not in the new data anymore
        self.end_old_memberships_after_parsing()

    def party_membership_processing(
        self,
        single_org_membership,
    ) -> None:

        need_to_add_voter_membership = single_org_membership["is_voter"]

        # get organization and on_behalf_of for the new membership
        organization = single_org_membership["organization"]
        on_behalf_of = single_org_membership["on_behalf_of"]

        # retrieve member and role for the new membership
        member = single_org_membership["member"]
        role = single_org_membership.get("role", "member")

        if membership := self.get_id_if_membership_is_parsed(single_org_membership):
            self.keep_membership_ids.append(membership.id)
            # Membership already exists and is active - no need to add or update
            print(
                "Membership already exists and is active - no need to add or update",
                membership,
            )
            return

        # check if independent member already has a voter membership in the main organization
        if existing_voter_membership := self.get_voter_membership_in_organization(
            member,
            organization.id,
        ):
            # if existing_voter_membership.on_behalf_of == single_org_membership["on_behalf_of"]:
            #     self.keep_membership_ids.append(existing_voter_membership.id)
            #     # User keep his voter membership in the main organization - no need to add new voter membership
            #     print("User keep his voter membership in the main organization - no need to add new voter membership")
            #     return
            if (
                existing_voter_membership.on_behalf_of == None
                and single_org_membership["on_behalf_of"] == None
            ):
                self.keep_membership_ids.append(existing_voter_membership.id)
                # User keep his voter membership in the main organization - no need to add new voter membership
                print(
                    "User keep his voter membership in the main organization - no need to add new voter membership"
                )
                return

        # get start & end time for the membership
        if start_time := single_org_membership.get("start_time"):
            pass
        else:
            start_time = self.default_start_time

        if end_time := single_org_membership.get("end_time"):
            pass
        else:
            end_time = (
                datetime.fromisoformat(start_time) - timedelta(seconds=1)
            ).isoformat()

        self.end_time = end_time

        # Get existing membership in the organization party
        if on_behalf_of:
            existing_organization_membership = (
                self.get_membership_in_organization_on_behalf_of(
                    member, on_behalf_of.id, None, exclude_role="voter"
                )
            )
        else:
            # it's a party voter membership without on_behalf_of who becoming independent member
            existing_organization_membership = None

        ## CHANGE ROLE ##
        # Check is user changed role in the same organization.
        # If yes, then end old membership and skip adding new voter membership.
        if (
            existing_organization_membership
            and existing_organization_membership.role != role
        ):
            print("CHANGE ROLE")
            # User changed role in the same organization - end old membership and skip adding new voter membership
            self.end_membership(existing_organization_membership, self.end_time)
            need_to_add_voter_membership = False

            existing_voter_membership = self.get_voter_membership_in_organization(
                member,
                organization.id,
            )
            if existing_voter_membership:
                if existing_voter_membership.on_behalf_of == on_behalf_of:
                    self.keep_membership_ids.append(existing_voter_membership.id)
                    # User keep his committee voter membership - no need to add new voter membership

        ## CHANGE PARTY ##
        # Check if user changed club. If yes then end old membership and voting membership.
        if not existing_organization_membership:
            print("CHANGE PARTY")
            # This is a party membership - check if user has existing voter membership in the main organization
            existing_voter_membership = self.get_membership_in_organization(
                member,
                organization.id,
            )
            party_group = (
                existing_voter_membership.on_behalf_of
                if existing_voter_membership
                else None
            )
            if party_group:
                existing_party_membership = self.get_membership_in_organization(
                    member,
                    party_group.id,
                )
                if existing_party_membership:
                    # End person's existing party membership and voter membership
                    self.end_membership(existing_party_membership, self.end_time)
                    self.end_membership(existing_voter_membership, self.end_time)
                    need_to_add_voter_membership = True
            else:
                if existing_voter_membership:
                    # This was an independent member amd mow is joining a party
                    # End the independent voter membership if exists
                    self.end_membership(existing_voter_membership, self.end_time)
                else:
                    # This is a new member joining a party
                    pass

        # Create party/committee membership if on_behalf_of exists
        org_id = None

        # This is a party membership - create membership in the party
        if on_behalf_of:
            org_id = on_behalf_of.id
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

    def committee_membership_processing(
        self,
        single_org_membership,
    ) -> None:

        role_membership_exists = False

        if membership := self.get_id_if_membership_is_parsed(single_org_membership):
            self.keep_membership_ids.append(membership.id)
            # Person keep his committee memberships, need to check if voter membership was changed
            role_membership_exists = True

        # get start & end time for the membership
        if start_time := single_org_membership.get("start_time"):
            pass
        else:
            start_time = self.default_start_time

        if end_time := single_org_membership.get("end_time"):
            pass
        else:
            end_time = (
                datetime.fromisoformat(start_time) - timedelta(seconds=1)
            ).isoformat()

        self.end_time = end_time

        need_to_add_voter_membership = single_org_membership["is_voter"]

        # get organization and on_behalf_of for the new membership
        organization = single_org_membership["organization"]
        on_behalf_of = single_org_membership["on_behalf_of"]

        # retrieve member and role for the new membership
        member = single_org_membership["member"]
        role = single_org_membership.get("role", "member")

        # Get existing membership in the organization committee.
        existing_organization_membership = (
            self.get_membership_in_organization_on_behalf_of(
                member, organization.id, None, exclude_role="voter"
            )
        )
        print(
            "EXISTING Committee MEMBERSHIP",
            existing_organization_membership,
            member,
            organization.id,
        )

        ## CHANGE ROLE ##
        # Check is user changed role in the same organization.
        # If yes, then end old membership and skip adding new voter membership.
        if role_membership_exists:
            print(
                "Membership already exists and is active - no need to add or update",
                membership,
            )
            self.keep_membership_ids.append(existing_organization_membership.id)
        else:
            if (
                existing_organization_membership
                and existing_organization_membership.role != role
            ):
                print("CHANGE ROLE")
                # User changed role in the same organization - end old membership and skip adding new voter membership
                print("END membership", existing_organization_membership)
                self.end_membership(existing_organization_membership, self.end_time)
                need_to_add_voter_membership = False

        ## CHANGE PARTY ##
        # Check if user changed club. If yes then end old voting membership and keep committee membership.
        if existing_organization_membership:
            print("CHANGE COMMITTEE")
            # Committee membership
            # Check if user has existing voter membership in the committee
            existing_voter_membership = self.get_voter_membership_in_organization(
                member,
                organization.id,
            )
            if existing_voter_membership:
                if existing_voter_membership.on_behalf_of == on_behalf_of:
                    self.keep_membership_ids.append(existing_voter_membership.id)
                    # User keep his committee voter membership - no need to add new voter membership
                else:
                    # User already has a committee membership - end just voter membership in the committee
                    print("END membership", existing_organization_membership)
                    self.end_membership(existing_voter_membership, self.end_time)
                    need_to_add_voter_membership = True

        if organization and not role_membership_exists:
            stored_membership = self.get_or_add_object(
                {
                    "member": member.id,
                    "organization": organization.id,
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
                        if (
                            membership.id not in self.keep_membership_ids
                            and membership.role == "voter"
                        ):
                            logger.info(
                                f"Found unparsed voter membership: person={person_id}, org={org_id}, on_behalf_of={on_behalf_id}"
                            )
                            memberships_to_end.append(membership)

        # End the voter memberships and their associated party memberships
        for voter_membership in memberships_to_end:
            logger.info(
                f"Ending voter membership {voter_membership.id} for person {voter_membership.member.id}"
            )
            print(voter_membership)

            # End the voter membership
            print("END membership", voter_membership)
            self.end_membership(voter_membership, self.end_time)

            # Find and end associated party membership (only if on_behalf_of exists)
            if voter_membership.organization.id == self.storage.main_org_id:
                if not voter_membership.on_behalf_of:
                    logger.info(
                        f"Independent member {voter_membership.member.id} - no party membership to end"
                    )
                    continue  # Independent member - no party membership to end
                party_membership = self.get_membership_in_organization(
                    voter_membership.member, voter_membership.on_behalf_of.id
                )
                if party_membership and party_membership.role in [
                    "member",
                    "president",
                    "deputy",
                ]:
                    logger.info(
                        f"Ending party membership {party_membership.id} for person {voter_membership.member.id}"
                    )
                    print("END party membership", party_membership)
                    self.end_membership(party_membership, self.end_time)
            else:
                # End committee membership if exists
                committee_membership = self.get_membership_in_organization(
                    voter_membership.member, voter_membership.organization.id
                )
                if committee_membership:
                    print("END committee membership", committee_membership)
                    self.end_membership(committee_membership, self.end_time)
