# Parladata base API


Python API with cacheing data for Parladata `https://github.com/danesjenovdan/parladata`

## Installation

Parladata base API is available on PyPI:

```console
$ python -m pip install parladata-base-api
```

## Quickstart
example:

```python
    >>> from parladata_base_api import DataStorage
    >>> storage = DataStorage(MANDATE, MANDATE_STARTIME, MAIN_ORG_ID, API_URL, API_USERNAME, API_PASSWORD)
    >>> perosn_object = storage.people_storage.get_or_add_object({"name": "Name Surname"})
```