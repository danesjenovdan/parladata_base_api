from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

from .api import Api


class PeopleApi(Api):
    endpoint = "people"

    def add_person_parser_name(self, person_id, parser_name) -> dict:
        return self._set_object(
            f"people/{person_id}/add_parser_name", {"parser_name": parser_name}
        )

    def upload_image(self, person_id, image_url) -> dict:
        file_name = f"/tmp/person_{person_id}.jpg"
        response = self._make_request("get", image_url)
        with open(file_name, "wb") as f:
            f.write(response.content)
        files = {"image": open(file_name, "rb")}

        return self._patch_object(person_id, data={}, files=files)


class OrganizationsApi(Api):
    endpoint = "organizations"


class SessionsApi(Api):
    endpoint = "sessions"

    def get_speech_count(self, id) -> int:
        date_str = datetime.now().date().strftime("%Y-%m-%d")
        url = f"{self.base_url}/speeches/count/?session={id}&valid_on={date_str}"
        response = self._make_request("get", url)
        data = response.json()
        if "count" in data.keys():
            return data["count"]
        else:
            return 0

    def unvalidate_speeches(self, session_id) -> dict:
        return self._set_object({}, custom_endpoint=f"{session_id}/unvalidate_speeches")


class VotesApi(Api):
    endpoint = "votes"

    def delete_vote_ballots(self, vote_id) -> dict:
        return self._delete_object(vote_id, custom_endpoint=f"delete_ballots")


class MotionsApi(Api):
    endpoint = "motions"


class AgendaItemsApi(Api):
    endpoint = "agenda-items"


class QuestionsApi(Api):
    endpoint = "questions"


class AnswersApi(Api):
    endpoint = "answers"


class PublicPersonQuestionsApi(Api):
    endpoint = "public-person-questions"


class PublicPersonAnswersApi(Api):
    endpoint = "public-person-answers"


class LegislationApi(Api):
    endpoint = "legislation"


class LegislationClassificationsApi(Api):
    endpoint = "legislation-classifications"


class ProceduresApi(Api):
    endpoint = "procedures"


class ProcedurePhasesApi(Api):
    endpoint = "procedure-phases"


class LegislationConsiderationApi(Api):
    endpoint = "legislation-consideration"


class LegislationStatusesApi(Api):
    endpoint = "legislation-status"


class PersonMembershipsApi(Api):
    endpoint = "person-memberships"


class OrganizationsMembershipsApi(Api):
    endpoint = "organization-memberships"


class AreasApi(Api):
    endpoint = "areas"


class SpeechesApi(Api):
    endpoint = "speeches"


class BallotsApi(Api):
    endpoint = "ballots"


class LinksApi(Api):
    endpoint = "links"


class MandatesApi(Api):
    endpoint = "mandates"


class ParladataApi(object):
    def __init__(
        self, api_url=None, api_user=None, api_password=None, json_data_path=None
    ):
        self.base_url = api_url
        self.json_data_path = json_data_path
        self.session = requests.Session()

        if self.base_url and api_user is not None and api_password is not None:
            self.session.auth = HTTPBasicAuth(api_user, api_password)

        self.sessions = SessionsApi(self.session, self.base_url, self.json_data_path)
        self.people = PeopleApi(self.session, self.base_url, self.json_data_path)
        self.organizations = OrganizationsApi(
            self.session, self.base_url, self.json_data_path
        )
        self.votes = VotesApi(self.session, self.base_url, self.json_data_path)
        self.motions = MotionsApi(self.session, self.base_url, self.json_data_path)
        self.agenda_items = AgendaItemsApi(
            self.session, self.base_url, self.json_data_path
        )
        self.questions = QuestionsApi(self.session, self.base_url, self.json_data_path)
        self.answers = AnswersApi(self.session, self.base_url, self.json_data_path)
        self.public_person_questions = PublicPersonQuestionsApi(
            self.session, self.base_url, self.json_data_path
        )
        self.public_person_answers = PublicPersonAnswersApi(
            self.session, self.base_url, self.json_data_path
        )
        self.legislation = LegislationApi(
            self.session, self.base_url, self.json_data_path
        )
        self.legislation_classifications = LegislationClassificationsApi(
            self.session, self.base_url, self.json_data_path
        )
        self.procedures = ProceduresApi(
            self.session, self.base_url, self.json_data_path
        )
        self.procedure_phases = ProcedurePhasesApi(
            self.session, self.base_url, self.json_data_path
        )
        self.legislation_consideration = LegislationConsiderationApi(
            self.session, self.base_url, self.json_data_path
        )
        self.legislation_statuses = LegislationStatusesApi(
            self.session, self.base_url, self.json_data_path
        )
        self.person_memberships = PersonMembershipsApi(
            self.session, self.base_url, self.json_data_path
        )
        self.organizations_memberships = OrganizationsMembershipsApi(
            self.session, self.base_url, self.json_data_path
        )
        self.areas = AreasApi(self.session, self.base_url, self.json_data_path)
        self.speeches = SpeechesApi(self.session, self.base_url, self.json_data_path)
        self.ballots = BallotsApi(self.session, self.base_url, self.json_data_path)
        self.links = LinksApi(self.session, self.base_url, self.json_data_path)
        self.mandates = MandatesApi(self.session, self.base_url, self.json_data_path)
