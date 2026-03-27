import json
import logging
from pathlib import Path

from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("logger")

RETRY = 1


class Api(object):
    def __init__(self, resquests_session, base_url=None, json_data_path=None):
        self.session = resquests_session
        self.base_url = base_url
        self.json_data_path = json_data_path
        endpoint = "base"

    @property
    def _use_json_storage(self):
        return bool(self.json_data_path) and not self.base_url

    @property
    def _json_file_path(self):
        return Path(self.json_data_path) / f"{self.endpoint}.json"

    def _load_json_payload(self):
        file_path = self._json_file_path
        if not file_path.exists():
            return {"count": 0, "next": None, "previous": None, "results": []}

        with file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if isinstance(payload, list):
            payload = {
                "count": len(payload),
                "next": None,
                "previous": None,
                "results": payload,
            }

        payload.setdefault("count", 0)
        payload.setdefault("next", None)
        payload.setdefault("previous", None)
        payload.setdefault("results", [])
        return payload

    def _save_json_payload(self, payload):
        payload["count"] = len(payload.get("results", []))
        payload["next"] = None
        payload["previous"] = None

        file_path = self._json_file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=4)

    @staticmethod
    def _match_query(obj, query):
        for key, value in query.items():
            if obj.get(key) == value:
                continue

            if str(obj.get(key)) != str(value):
                return False
        return True

    @staticmethod
    def _find_object_index(results, object_id):
        for index, obj in enumerate(results):
            if str(obj.get("id")) == str(object_id):
                return index
        return None

    @retry(
        stop=stop_after_attempt(RETRY),
        wait=wait_exponential(multiplier=10, min=5, max=60),
    )
    def _make_request(self, method, url, **kwargs):
        """Make an HTTP request with retry logic (GET, POST, PATCH, DELETE)."""
        func = getattr(self.session, method)
        response = func(url, timeout=10, **kwargs)
        if response.status_code > 299:
            raise RequestException(
                f"API error {response.status_code}: {response.content}"
            )
        return response

    def _get_data_from_pager_api_gen(self, url, limit=300):
        if "?" in url:
            url = url + f"&limit={limit}"
        else:
            url = url + f"?limit={limit}"
        while url:
            response = self._make_request("get", url)
            data = response.json()
            yield data["results"]
            url = data["next"]

    def _get_objects(self, limit=300, *args, **kwargs):
        if self._use_json_storage:
            payload = self._load_json_payload()
            results = payload.get("results", [])

            if kwargs:
                results = [obj for obj in results if self._match_query(obj, kwargs)]

            return results[:limit]
        url = f"{self.base_url}/{self.endpoint}"

        args = "&".join([f"{key}={value}" for key, value in kwargs.items()])
        if args:
            if "?" in url:
                url = url + "&" + args
            else:
                url = url + "?" + args

        return [
            obj
            for page in self._get_data_from_pager_api_gen(url, limit)
            for obj in page
        ]

    def _get_object(self, object_id, custom_endpoint=None):
        if self._use_json_storage:
            if custom_endpoint:
                raise NotImplementedError(
                    "custom_endpoint is not supported in JSON storage mode for GET"
                )

            payload = self._load_json_payload()
            results = payload.get("results", [])
            index = self._find_object_index(results, object_id)
            if index is None:
                raise RequestException(f"Object with ID={object_id} does not exist")

            return results[index]

        url = f"{self.base_url}/{self.endpoint}/{object_id}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        response = self._make_request("get", url)
        return response.json()

    def _set_object(self, data, custom_endpoint=None):
        if self._use_json_storage:
            if custom_endpoint:
                raise NotImplementedError(
                    "custom_endpoint is not supported in JSON storage mode for POST"
                )

            payload = self._load_json_payload()
            results = payload.get("results", [])

            new_object = dict(data)
            if "id" not in new_object:
                max_id = max((obj.get("id", 0) for obj in results), default=0)
                new_object["id"] = max_id + 1

            results.append(new_object)
            payload["results"] = results
            self._save_json_payload(payload)
            return new_object

        url = f"{self.base_url}/{self.endpoint}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        response = self._make_request("post", url, json=data)
        return response.json()

    def _patch_object(self, object_id, data, custom_endpoint=None, files=None):
        if self._use_json_storage:
            if custom_endpoint:
                raise NotImplementedError(
                    "custom_endpoint is not supported in JSON storage mode for PATCH"
                )
            if files:
                raise NotImplementedError(
                    "`files` is not supported in JSON storage mode"
                )

            payload = self._load_json_payload()
            results = payload.get("results", [])
            index = self._find_object_index(results, object_id)
            if index is None:
                raise RequestException(f"Object with ID={object_id} does not exist")

            results[index].update(data)
            updated_object = results[index]
            payload["results"] = results
            self._save_json_payload(payload)
            return updated_object

        url = f"{self.base_url}/{self.endpoint}/{object_id}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        if files:
            response = self._make_request("patch", url, files=files)
        else:
            response = self._make_request("patch", url, json=data)
        return response.json()

    def _delete_object(self, object_id, custom_endpoint=None):
        if self._use_json_storage:
            if custom_endpoint:
                raise NotImplementedError(
                    "custom_endpoint is not supported in JSON storage mode for DELETE"
                )

            payload = self._load_json_payload()
            results = payload.get("results", [])
            index = self._find_object_index(results, object_id)
            if index is None:
                raise RequestException(f"Object with ID={object_id} does not exist")

            deleted_object = results.pop(index)
            payload["results"] = results
            self._save_json_payload(payload)
            return deleted_object

        url = f"{self.base_url}/{self.endpoint}/{object_id}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        response = self._make_request("delete", url)
        return response.json()

    def get_all(self, limit=300, *args, **kwargs) -> list:
        return self._get_objects(limit, *args, **kwargs)

    def get(self, person_id) -> dict:
        return self._get_object(person_id)

    def set(self, data) -> dict:
        return self._set_object(data)

    def patch(self, object_id, data, files=None) -> dict:
        return self._patch_object(object_id, data, files=files)

    def delete(self, person_id) -> dict:
        return self._delete_object(person_id)
