import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parladata_base_api.api.endpoints import PeopleApi


class ApiJsonStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.json_dir = self.temp_dir.name
        self.people_file = Path(self.json_dir) / "people.json"

        payload = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {"id": 1, "name": "Ana", "parser_names": "ana"},
                {"id": 2, "name": "Bine", "parser_names": "bine"},
            ],
        }
        with self.people_file.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=4)

        self.api = PeopleApi(resquests_session=None, json_data_path=self.json_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _read_results(self):
        with self.people_file.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload["results"]

    def test_get_all_and_filtering(self):
        all_people = self.api.get_all()
        self.assertEqual(len(all_people), 2)

        filtered_people = self.api.get_all(name="Ana")
        self.assertEqual(len(filtered_people), 1)
        self.assertEqual(filtered_people[0]["id"], 1)

    def test_post_patch_delete_flow(self):
        created = self.api.set({"name": "Cene", "parser_names": "cene"})
        self.assertEqual(created["id"], 3)

        fetched = self.api.get(3)
        self.assertEqual(fetched["name"], "Cene")

        patched = self.api.patch(3, {"name": "Cene Novak"})
        self.assertEqual(patched["name"], "Cene Novak")

        deleted = self.api.delete(3)
        self.assertEqual(deleted["id"], 3)

        results = self._read_results()
        self.assertEqual(len(results), 2)
        self.assertFalse(any(item["id"] == 3 for item in results))

    def test_post_creates_new_file_when_missing(self):
        os.remove(self.people_file)

        created = self.api.set({"name": "Dora", "parser_names": "dora"})
        self.assertEqual(created["id"], 1)

        results = self._read_results()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Dora")


if __name__ == "__main__":
    unittest.main()
