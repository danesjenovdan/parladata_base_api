import logging

from parladata_base_api.api.endpoints import ParladataApi
from parladata_base_api.storages.area_storage import AreaStorage
from parladata_base_api.storages.legislation_storage import LegislationStorage
from parladata_base_api.storages.membership_storage import MembershipStorage
from parladata_base_api.storages.organization_membership_storage import (
    OrganizationMembershipStorage,
)
from parladata_base_api.storages.organization_storage import OrganizationStorage
from parladata_base_api.storages.people_storage import PeopleStorage
from parladata_base_api.storages.public_question_storage import PublicQuestionStorage
from parladata_base_api.storages.question_storage import QuestionStorage
from parladata_base_api.storages.session_storage import SessionStorage


class DataStorage(object):
    default_procedure_phase = 1

    def __init__(
        self,
        mandate_id: int,
        mandate_start_time: str,
        main_org_id: int,
        api_url: str,
        api_auth_username: str,
        api_auth_password: str,
    ) -> None:
        self.mandate_start_time = mandate_start_time
        self.mandate_id = mandate_id
        self.main_org_id = main_org_id

        self.parladata_api = ParladataApi(api_url, api_auth_username, api_auth_password)

        logging.info(
            f"Initialize storages for mandate {mandate_id} with start time {mandate_start_time}"
        )
        self.session_storage = SessionStorage(self)
        self.legislation_storage = LegislationStorage(self)
        self.people_storage = PeopleStorage(self)
        self.organization_storage = OrganizationStorage(self)
        self.question_storage = QuestionStorage(self)
        self.public_question_storage = PublicQuestionStorage(self)
        self.membership_storage = MembershipStorage(self)
        self.area_storage = AreaStorage(self)
        self.organization_membership_storage = OrganizationMembershipStorage(self)
