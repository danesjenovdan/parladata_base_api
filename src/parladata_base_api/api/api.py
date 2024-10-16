import logging

from requests.auth import HTTPBasicAuth

logger = logging.getLogger("logger")


class Api(object):
    def __init__(self, resquests_session, base_url):
        self.session = resquests_session
        self.base_url = base_url
        endpoint = "base"

    def _get_data_from_pager_api_gen(self, url, limit=300):
        end = False
        page = 1
        if "?" in url:
            url = url + f"&limit={limit}"
        else:
            url = url + f"?limit={limit}"
        while url:
            response = self.session.get(url)
            if response.status_code != 200:
                logger.warning(response.content)
                logger.warning(url)
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
        response = self.session.get(url)
        if response.status_code > 299:
            logger.warning(response.content)
            logger.warning(url)
        return response.json()

    def _set_object(self, data, custom_endpoint=None):
        url = f"{self.base_url}/{self.endpoint}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        response = self.session.post(url, json=data)
        if response.status_code > 299:
            logger.warning(response.content)
            logger.warning(url)
        return response.json()

    def _patch_object(self, object_id, data, custom_endpoint=None, files=None):
        url = f"{self.base_url}/{self.endpoint}/{object_id}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        if files:
            response = self.session.patch(url, files=files)
        else:
            response = self.session.patch(url, json=data)
        if response.status_code > 299:
            logger.warning(response.content)
            logger.warning(url)
        return response.json()

    def _delete_object(self, object_id, custom_endpoint=None):
        url = f"{self.base_url}/{self.endpoint}/{object_id}/" + (
            f"{custom_endpoint}/" if custom_endpoint else ""
        )
        response = self.session.delete(url)
        if response.status_code > 299:
            logger.warning(response.content)
            logger.warning(url)
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
