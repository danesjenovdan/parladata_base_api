import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Make local test modules and src package importable.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data import generate_test_data
from membership_update_integration import ParladataAPIUpdateTester, update_data


class MembershipUpdateIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.json_dir = Path(cls.temp_dir.name) / "json_store"

        source_dir = Path(__file__).parent / "json_data_store"
        shutil.copytree(source_dir, cls.json_dir)

        # 1) Run update flow against copied JSON store.
        update_data(db_mode=False, update_test=True, json_data_path=str(cls.json_dir))

        # 2) Initialize storage view on top of updated JSON store.
        cls.tester = ParladataAPIUpdateTester(
            json_data_path=str(cls.json_dir),
            update_test=True,
        )
        cls.tester.test_data = generate_test_data()
        cls.tester.initialize_storage()

        cls.storage = cls.tester.temp_storage
        cls.storage.organization_storage.load_data()
        cls.storage.people_storage.load_data()
        cls.storage.membership_storage.load_data()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def _read_results(self, filename):
        file_path = self.json_dir / filename
        with file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload["results"]

    def _people_id_by_name(self):
        people = self._read_results("people.json")
        return {person["name"]: person["id"] for person in people}

    def _organizations_id_by_name(self):
        organizations = self._read_results("organizations.json")
        return {org["name"]: org["id"] for org in organizations}

    def _active_json_memberships(self, member_id):
        memberships = self._read_results("person-memberships.json")
        return [
            membership
            for membership in memberships
            if membership["member"] == member_id and membership["end_time"] is None
        ]

    def test_update_pipeline_loads_json_and_storage(self):
        json_memberships = self._read_results("person-memberships.json")
        self.assertGreater(len(json_memberships), 0)

        self.assertGreater(len(self.storage.membership_storage.memberships), 0)

    def test_david_has_active_party_membership_in_pg3_json_and_storage(self):
        people_map = self._people_id_by_name()
        david_id = people_map["David Krajnc"]

        pg3_id = self._organizations_id_by_name()["Green Movement"]

        # Organization IDs from test data: pg1=3, pg2=4, pg3=5.
        active_json = self._active_json_memberships(david_id)
        active_json_party = [
            item for item in active_json if item["organization"] in {3, 4, 5}
        ]
        self.assertTrue(
            any(
                item["organization"] == pg3_id and item["role"] == "member"
                for item in active_json_party
            )
        )

        person = self.storage.people_storage.get_person_by_id(david_id)
        active_storage_party = [
            membership
            for membership in person.active_memberships
            if membership.organization and membership.organization.id in {3, 4, 5}
        ]
        self.assertTrue(
            any(
                membership.organization.id == pg3_id and membership.role == "member"
                for membership in active_storage_party
            )
        )

        # Test commitee on beahf of is pg3
        active_storage_committee_on_behalf_of_pg3 = [
            membership
            for membership in person.active_memberships
            if membership.on_behalf_of
            and membership.on_behalf_of.id == pg3_id
            and membership.role == "voter"
            and membership.organization
            and membership.organization.id != 2
        ]
        self.assertEqual(len(active_storage_committee_on_behalf_of_pg3), 1)

    def test_anna_has_no_active_party_membership_json_and_storage(self):
        people_map = self._people_id_by_name()
        anna_id = people_map["Anna Novak"]

        active_json = self._active_json_memberships(anna_id)
        active_json_party = [
            item for item in active_json if item["organization"] in {3, 4, 5}
        ]
        self.assertEqual(len(active_json_party), 0)

        person = self.storage.people_storage.get_person_by_id(anna_id)
        active_storage_party = [
            membership
            for membership in person.active_memberships
            if membership.organization and membership.organization.id in {3, 4, 5}
        ]
        self.assertEqual(len(active_storage_party), 0)

        # check if Anna has active unaffiliated membership (voter in house without party)
        active_storage_unaffiliated = [
            membership
            for membership in person.active_memberships
            if membership.on_behalf_of == None
            and membership.role == "voter"
            and membership.organization
            and membership.organization.id == 2
        ]
        self.assertGreater(len(active_storage_unaffiliated), 0)

    def test_cecilia_has_all_memberships_ended_in_json_and_storage(self):
        people_map = self._people_id_by_name()
        cecilija_id = people_map["Cecilia Horvat"]

        json_memberships = self._read_results("person-memberships.json")
        cecilija_memberships = [
            item for item in json_memberships if item["member"] == cecilija_id
        ]
        self.assertGreater(len(cecilija_memberships), 0)
        self.assertTrue(
            all(item["end_time"] is not None for item in cecilija_memberships)
        )

        person = self.storage.people_storage.get_person_by_id(cecilija_id)
        self.assertGreater(len(person.active_memberships), 0)
        self.assertTrue(
            all(
                membership.end_time is not None
                for membership in person.active_memberships
            )
        )

    def test_jana_become_a_president_of_pg3_in_json_and_storage(self):
        people_map = self._people_id_by_name()
        jana_id = people_map["Jana Vidmar"]

        pg3_id = self._organizations_id_by_name()["Green Movement"]
        json_memberships = self._read_results("person-memberships.json")
        jana_pg3 = [
            item
            for item in json_memberships
            if item["member"] == jana_id
            and item["organization"] == pg3_id
            and item["end_time"] is None
        ]
        self.assertEqual(len(jana_pg3), 1)
        self.assertEqual(jana_pg3[0]["role"], "president")

        person = self.storage.people_storage.get_person_by_id(jana_id)
        jana_pg3_storage = [
            membership
            for membership in person.active_memberships
            if membership.organization and membership.organization.id == pg3_id
        ]
        self.assertEqual(len(jana_pg3_storage), 1)
        self.assertEqual(jana_pg3_storage[0].role, "president")

    def test_filip_has_ended_membership_in_commitee(self):
        people_map = self._people_id_by_name()
        filip_id = people_map["Filip Mlakar"]

        json_memberships = self._read_results("person-memberships.json")
        filip_commitee = [
            item
            for item in json_memberships
            if item["member"] == filip_id
            and item["organization"] != 2
            and item["role"] == "voter"
        ]
        self.assertEqual(len(filip_commitee), 1)
        self.assertIsNotNone(filip_commitee[0]["end_time"])

        person = self.storage.people_storage.get_person_by_id(filip_id)
        filip_commitee_storage = [
            membership
            for membership in person.active_memberships
            if membership.organization
            and membership.organization.id != 2
            and membership.role == "voter"
        ]
        self.assertEqual(len(filip_commitee_storage), 0)


if __name__ == "__main__":
    unittest.main()
