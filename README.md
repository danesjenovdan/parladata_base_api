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


# Membership parser
Prepare memberships for each user:
```python
per_person_data = defaultdict(lambda: defaultdict(list))
# save data for each person
per_person_data[person_id][organization_type].append(membership_dict)
# update memebrship data in parladata
membership_storage.refresh_per_person_memberships(
    per_person_data, main_org_obj
)
```


Example for per_person_data
```
{40:
    {
        'committee': [
        {
            'is_voter': True,
            'member': <Person Janez Janez [40]>,
            'organization': <Organization: Odbor za zunanjo politiko [34]>,
            'on_behalf_of': None,
            'role': 'member',
            'type': 'committee',
            'mandate': '2'
        }, {
            'is_voter': True,
            'member': <Person Janez Janez [40]>,
            'organization': <Organization: Ustavna komisija [88]>,
            'on_behalf_of': None,
            'role': 'member',
            'type': 'committee',
            'mandate': '2'
        }], 
        'party': [{
            'is_voter': True,
            'member': <Person Janez Janez [40]>,
            'organization': <Organization: Slovenska demonstracijska stranka [2]>,
            'on_behalf_of': None,
            'role': 'member',
            'type': 'party',
            'mandate': '2'
        }]
    },
}
```