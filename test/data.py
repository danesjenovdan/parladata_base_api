"""
Test data generator for Parladata Base API

This module generates comprehensive test data for testing the membership
management functionality of the Parladata Base API, including:
- Mandate
- Organizations (root, house, parliamentary groups, committees)
- People (members of parliament)
- Organization memberships (organizational hierarchy)
- Person memberships (voting rights and party affiliations)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List


class TestDataGenerator:
    """Generate structured test data for Parladata Base API testing"""

    def __init__(self, mandate_start_date: str = "2022-01-01T00:00:00"):
        self.mandate_start_date = mandate_start_date
        self.membership_change_date = "2026-01-15T00:00:00"
        self.mandate_end_date = "2026-12-31"

        # Auto-incrementing IDs (for mock data - real IDs will come from API)
        self._next_org_id = 1
        self._next_person_id = 1
        self._next_membership_id = 1
        self._next_org_membership_id = 1

        # Storage for generated objects
        self.mandate = None
        self.organizations = {}
        self.people = {}
        self.people2 = {}
        self.organization_memberships = []
        self.person_memberships = []
        self.person_memberships2 = []
        self.house = None

    def generate_all(self) -> Dict[str, Any]:
        """Generate complete test dataset"""
        self._generate_mandate()
        self._generate_organizations()
        self._generate_people()
        self._generate_organization_memberships()
        self._generate_person_memberships()

        return {
            "mandate": self.mandate,
            "organizations": list(self.organizations.values()),
            "people": list(self.people.values()),
            "people2": list(self.people2.values()),
            "organization_memberships": self.organization_memberships,
            "person_memberships": self.person_memberships,
            "person_memberships2": self.person_memberships2,
            "house": self.organizations["house"],
        }

    def _generate_mandate(self) -> None:
        """Generate test mandate"""
        self.mandate = {
            "id": 1,
            "description": "Test Mandate 2022-2026",
            "beginning": self.mandate_start_date,
            "end": self.mandate_end_date,
        }

    def _generate_organizations(self) -> None:
        """Generate organizational hierarchy"""

        # 1. Root organization
        self.organizations["root"] = {
            "id": self._next_org_id,
            "name": "Test Country",
            "parser_names": "test country|country",
            "classification": "root",
            "gov_id": "ROOT-001",
        }
        self._next_org_id += 1

        # 2. House (krovna organizacija - main deliberative body)
        self.organizations["house"] = {
            "id": self._next_org_id,
            "name": "National Assembly",
            "parser_names": "national assembly|assembly",
            "classification": "house",
            "gov_id": "HOUSE-001",
        }
        self._next_org_id += 1

        # 3. Parliamentary groups (poslanske skupine)
        parliamentary_groups = [
            {
                "key": "pg1",
                "name": "Progressive Party Group",
                "short": "PPG",
                "parser_names": "progressive party group|pg1|ppg",
                "gov_id": "PG-001",
            },
            {
                "key": "pg2",
                "name": "Conservative Alliance",
                "short": "CA",
                "parser_names": "conservative alliance|pg2|ca",
                "gov_id": "PG-002",
            },
            {
                "key": "pg3",
                "name": "Green Movement",
                "short": "GM",
                "parser_names": "green movement|pg3|gm",
                "gov_id": "PG-003",
            },
        ]

        for pg in parliamentary_groups:
            self.organizations[pg["key"]] = {
                "id": self._next_org_id,
                "name": pg["name"],
                "parser_names": pg["parser_names"],
                "classification": "pg",
                "gov_id": pg["gov_id"],
            }
            self._next_org_id += 1

        # 4. Committees (odbori)
        committees = [
            {
                "key": "committee1",
                "name": "Committee on Finance",
                "parser_names": "committee on finance|finance committee|committee1",
                "gov_id": "COM-001",
            },
            {
                "key": "committee2",
                "name": "Committee on Health",
                "parser_names": "committee on health|health committee|committee2",
                "gov_id": "COM-002",
            },
        ]

        for committee in committees:
            self.organizations[committee["key"]] = {
                "id": self._next_org_id,
                "name": committee["name"],
                "parser_names": committee["parser_names"],
                "classification": "committee",
                "gov_id": committee["gov_id"],
            }
            self._next_org_id += 1

    def _generate_people(self) -> None:
        """Generate members of parliament distributed across parliamentary groups"""

        # Define member distribution per parliamentary group
        pg_members_org = {
            "pg1": [
                {"name": "Anna Novak", "role": "president"},
                {"name": "Boris Kovač", "role": "deputy"},
                {"name": "Cecilia Horvat", "role": "member"},
                {"name": "David Krajnc", "role": "member"},
                {"name": "Eva Zupan", "role": "member"},
            ],
            "pg2": [
                {"name": "Filip Mlakar", "role": "president"},
                {"name": "Greta Potočnik", "role": "deputy"},
                {"name": "Henrik Pavlič", "role": "member"},
                {"name": "Irena Golob", "role": "member"},
            ],
            "pg3": [
                {
                    "name": "Jana Vidmar",
                    "role": "member",
                },
            ],
        }
        pg_members_edited = {
            "pg1": [
                {"name": "Boris Kovač", "role": "president"},
                {"name": "Eva Zupan", "role": "member"},
            ],
            "pg2": [
                {"name": "Filip Mlakar", "role": "president"},
                {"name": "Greta Potočnik", "role": "deputy"},
                {"name": "Henrik Pavlič", "role": "member"},
                {"name": "Irena Golob", "role": "member"},
            ],
            "pg3": [
                {
                    "name": "Jana Vidmar",
                    "role": "president",
                },
                {"name": "David Krajnc", "role": "member"},
            ],
            "unaffiliated": [
                {"name": "Anna Novak"},
            ],
        }
        self.wb_members_org = {
            "committee1": [  # Committee on Finance
                {"name": "David Krajnc", "role": "president"},
                {"name": "Cecilia Horvat", "role": "member"},
                {"name": "Anna Novak", "role": "member"},
                {"name": "Filip Mlakar", "role": "deputy"},
            ],
            "committee2": [  # Committee on Health
                {"name": "Irena Golob", "role": "president"},
                {"name": "Greta Potočnik", "role": "member"},
                {"name": "Anna Novak", "role": "member"},
            ],
        }
        self.wb_members_edited = {
            "committee1": [  # Committee on Finance
                {"name": "David Krajnc", "role": "president"},
                {"name": "Anna Novak", "role": "member"},
                {"name": "Greta Potočnik", "role": "member"},
            ],
            "committee2": [  # Committee on Health
                {"name": "Irena Golob", "role": "member"},
                {"name": "Greta Potočnik", "role": "president"},
                {"name": "Anna Novak", "role": "member"},
            ],
        }

        for pg_key, members in pg_members_org.items():
            for member in members:
                person_key = f"person_{self._next_person_id}"
                name_parts = member["name"].lower().split()
                parser_names = (
                    f"{member['name'].lower()}|{name_parts[0]} {name_parts[1]}"
                )

                self.people[person_key] = {
                    "id": self._next_person_id,
                    "name": member["name"],
                    "parser_names": parser_names,
                    "gov_id": f"PER-{self._next_person_id:03d}",
                    "_pg_key": pg_key,  # Internal reference
                    "_pg_role": member["role"],  # Internal reference
                }
                self._next_person_id += 1

        self._next_person_id = 1
        for pg_key, members in pg_members_edited.items():
            for member in members:
                person_key = f"person2_{self._next_person_id}"
                name_parts = member["name"].lower().split()
                parser_names = (
                    f"{member['name'].lower()}|{name_parts[0]} {name_parts[1]}"
                )

                self.people2[person_key] = {
                    "id": self._next_person_id,
                    "name": member["name"],
                    "parser_names": parser_names,
                    "gov_id": f"PER-{self._next_person_id:03d}",
                    "_pg_key": pg_key,  # Internal reference
                    "_pg_role": member.get("role", None),  # Internal reference
                }
                self._next_person_id += 1

    def _generate_organization_memberships(self) -> None:
        """
        Generate organization membership hierarchy:
        - House is member of Root
        - Parliamentary groups are members of House
        """

        # House in Root organization
        self.organization_memberships.append(
            {
                "id": self._next_org_membership_id,
                "member": self.organizations["house"]["id"],
                "organization": self.organizations["root"]["id"],
                "start_time": self.mandate_start_date,
                "end_time": None,
            }
        )
        self._next_org_membership_id += 1

        # Parliamentary groups in House
        for pg_key in ["pg1", "pg2", "pg3"]:
            self.organization_memberships.append(
                {
                    "id": self._next_org_membership_id,
                    "member": self.organizations[pg_key]["id"],
                    "organization": self.organizations["house"]["id"],
                    "start_time": self.mandate_start_date,
                    "end_time": None,
                }
            )
            self._next_org_membership_id += 1

    def _generate_person_memberships(self) -> None:
        """
        Generate person memberships:
        1. Party membership in parliamentary group (role: president/deputy/member)
        2. Voter membership in House (role: voter, on_behalf_of: parliamentary group)
        """

        for person_key, person in self.people.items():
            pg_key = person["_pg_key"]
            pg_role = person["_pg_role"]

            # 1. Party membership in parliamentary group
            self.person_memberships.append(
                {
                    "member": person["name"],
                    "organization": pg_key,
                    "role": pg_role,
                    "start_time": self.mandate_start_date,
                    "end_time": None,
                    "on_behalf_of": None,
                    "voter": True,
                    "type": "party",
                }
            )

        for wb_key, wb_members in self.wb_members_org.items():
            for wb_member in wb_members:
                self.person_memberships.append(
                    {
                        "member": wb_member["name"],
                        "organization": wb_key,
                        "role": wb_member["role"],
                        "start_time": self.mandate_start_date,
                        "end_time": None,
                        "on_behalf_of": None,
                        "voter": True,
                        "type": "committee",
                    }
                )

        for person_key, person in self.people2.items():
            pg_key = person["_pg_key"]
            pg_role = person.get("_pg_role", None)
            if pg_key == "unaffiliated":
                pg_id = None
            else:
                pg_id = self.organizations[pg_key]["id"]
            house_id = self.organizations["house"]["id"]

            # 1. Party membership in parliamentary group
            self.person_memberships2.append(
                {
                    "member": person["name"],
                    "organization": pg_key,
                    "role": pg_role,
                    "start_time": self.mandate_start_date,
                    "end_time": None,
                    "on_behalf_of": None,
                    "voter": True,
                    "type": "party",
                }
            )

        for wb_key, wb_members in self.wb_members_edited.items():
            for wb_member in wb_members:
                self.person_memberships2.append(
                    {
                        "member": wb_member["name"],
                        "organization": wb_key,
                        "role": wb_member["role"],
                        "start_time": self.mandate_start_date,
                        "end_time": None,
                        "on_behalf_of": None,
                        "voter": True,
                        "type": "committee",
                    }
                )

    def get_summary(self) -> str:
        """Generate a human-readable summary of the test data"""
        lines = [
            "=" * 70,
            "TEST DATA SUMMARY",
            "=" * 70,
            "",
            f"Mandate: {self.mandate['description']}",
            f"Period: {self.mandate['beginning']} - {self.mandate['end']}",
            "",
            "Organizations:",
            f"  - Root: {self.organizations['root']['name']}",
            f"  - House: {self.organizations['house']['name']}",
            "  - Parliamentary Groups:",
        ]

        for pg_key in ["pg1", "pg2", "pg3"]:
            pg = self.organizations[pg_key]
            member_count = sum(
                1 for p in self.people.values() if p["_pg_key"] == pg_key
            )
            lines.append(f"      * {pg['name']} ({member_count} members)")

        lines.extend(
            [
                "  - Committees:",
                f"      * {self.organizations['committee1']['name']}",
                f"      * {self.organizations['committee2']['name']}",
                "",
                f"Total People: {len(self.people)}",
            ]
        )

        lines.extend(
            [
                "Version 1 - Original memberships",
            ]
        )
        for pg_key in ["pg1", "pg2", "pg3"]:
            pg = self.organizations[pg_key]
            members = [p for p in self.people.values() if p["_pg_key"] == pg_key]
            lines.append(f"  {pg['name']}:")
            for person in members:
                lines.append(f"    - {person['name']} ({person['_pg_role']})")

        lines.extend(
            [
                "",
                f"Organization Memberships: {len(self.organization_memberships)}",
                f"Person Memberships: {len(self.person_memberships)}",
                "=" * 70,
            ]
        )
        lines.extend(
            [
                "Version 2 - Edited memberships",
            ]
        )
        for pg_key in ["pg1", "pg2", "pg3", "unaffiliated"]:
            pg = self.organizations.get(pg_key, {"name": pg_key})
            members = [p for p in self.people2.values() if p["_pg_key"] == pg_key]
            lines.append(f"  {pg['name']}:")
            for person in members:
                role = person.get("_pg_role", "member")
                lines.append(f"    - {person['name']} ({role})")

        return "\n".join(lines)


def generate_test_data() -> Dict[str, Any]:
    """
    Convenience function to generate complete test dataset

    Returns:
        Dictionary containing all test data:
        - mandate
        - organizations (list)
        - people (list)
        - organization_memberships (list)
        - person_memberships (list)
    """
    generator = TestDataGenerator()
    data = generator.generate_all()

    # Print summary
    print(generator.get_summary())

    return data
