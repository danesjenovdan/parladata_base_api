import logging

from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("logger")


class Api(object):
    def __init__(self, resquests_session, base_url):
        self.session = resquests_session
        self.base_url = base_url
        endpoint = "base"

    @retry(
        stop=stop_after_attempt(5), wait=wait_exponential(multiplier=10, min=5, max=60)
    )
    def _make_request(self, method, url, **kwargs):
        """Naredi HTTP zahtevo s retry logiko (GET, POST, PATCH, DELETE)."""
        func = getattr(self.session, method)
        response = func(url, timeout=10, **kwargs)
        if response.status_code > 299:
            raise RequestException(
                f"API napaka {response.status_code}: {response.content}"
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
        url = f"{self.base_url}/{self.endpoint}/{object_id}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        response = self._make_request("get", url)
        return response.json()

    def _set_object(self, data, custom_endpoint=None):
        url = f"{self.base_url}/{self.endpoint}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        response = self._make_request("post", url, json=data)
        return response.json()

    def _patch_object(self, object_id, data, custom_endpoint=None, files=None):
        url = f"{self.base_url}/{self.endpoint}/{object_id}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        if files:
            response = self._make_request("patch", url, files=files)
        else:
            response = self._make_request("patch", url, json=data)
        return response.json()

    def _delete_object(self, object_id, custom_endpoint=None):
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
