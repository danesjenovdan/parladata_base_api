import logging

from parladata_base_api.storages.agenda_item_storage import AgendaItemStorage
from parladata_base_api.storages.utils import ParladataObject, Storage
from parladata_base_api.storages.vote_storage import VoteStorage

logger = logging.getLogger("logger")


class Session(ParladataObject):
    keys = ["gov_id"]

    def __init__(
        self,
        name: str,
        gov_id: str,
        id: int,
        organizations: list,
        start_time: str | None,
        end_time: str | None,
        mandate: int,
        is_new: bool,
        in_review: bool,
        core_storage,
        parladata_api,
    ) -> None:
        # session members
        self.id = id
        self.name = name
        self.organizations = organizations
        self.count = None
        self.start_time = start_time
        self.end_time = end_time
        self.gov_id = gov_id
        self.is_new = is_new
        self.in_review = in_review
        self.mandate = mandate
        self.storage = core_storage
        self.parladata_api = parladata_api

        # session children
        self.vote_storage = VoteStorage(self.storage, self)
        self.agenda_items_storage = AgendaItemStorage(self.storage, self)

    def __str__(self):
        return f"{self.name} [{self.id}]"

    def get_speech_count(self) -> int:
        if self.count == None:
            self.count = self.parladata_api.sessions.get_speech_count(self.id)
        return self.count

    def unvalidate_speeches(self) -> None:
        self.parladata_api.sessions.unvalidate_speeches(self.id)

    def add_speeches(self, data) -> None:
        chunks = [data[x : x + 50] for x in range(0, len(data), 50)]
        logger.debug(f"Adding {len(chunks)} speech chunks")
        for chunk in chunks:
            self.parladata_api.speeches.set(chunk)

    def update_start_time(self, timestamp) -> None:
        self.parladata_api.sessions.patch(
            self.id, {"start_time": timestamp.isoformat()}
        )
        self.start_time = timestamp.isoformat()

    def update_end_time(self, timestamp) -> None:
        self.parladata_api.sessions.patch(self.id, {"end_time": timestamp.isoformat()})
        self.end_time = timestamp.isoformat()

    def patch_session(self, data) -> None:
        self.parladata_api.sessions.patch(self.id, data)


class SessionStorage(Storage):
    def __init__(self, core_storage) -> None:
        super().__init__(core_storage)

        self.sessions = {}
        self.dz_sessions_by_names = {}
        self.sessions_in_review = []

    def load_data(self):
        for session in self.parladata_api.sessions.get_all(
            mandate=self.storage.mandate_id
        ):
            self.store_object(session, is_new=False)

    def store_object(self, session, is_new) -> Session:
        temp_session = Session(
            name=session["name"],
            gov_id=session["gov_id"],
            id=session["id"],
            organizations=session["organizations"],
            start_time=session["start_time"],
            end_time=session["end_time"],
            mandate=session["mandate"],
            is_new=is_new,
            in_review=session["in_review"],
            core_storage=self.storage,
            parladata_api=self.parladata_api,
        )
        self.sessions[temp_session.get_key()] = temp_session
        self.dz_sessions_by_names[temp_session.name.lower()] = temp_session
        if temp_session.in_review:
            self.sessions_in_review.append(temp_session)
        return temp_session

    def get_or_add_object(self, data: dict) -> Session:
        if not self.sessions:
            self.load_data()
        key = Session.get_key_from_dict(data)
        if key in self.sessions.keys():
            return self.sessions[key]
        else:
            data.update(mandate=self.storage.mandate_id)
            session = self.parladata_api.sessions.set(data)
            return self.store_object(session, is_new=True)

    def get_object_or_none(self, data: dict) -> Session:
        if not self.sessions:
            self.load_data()
        key = Session.get_key_from_dict(data)
        return self.sessions.get(key, None)

    def patch_session(self, session: Session, data: dict) -> None:
        self.parladata_api.sessions.set(session.id, data)

        # remove session from sessions_in_review if setted to in_review=False
        if not data.get("in_review", True):
            self.sessions_in_review.remove(session)

        # add session to sessions_in_review if setted to in_review=True
        if data.get("in_review", False):
            self.sessions_in_review.append(session)

    def is_session_in_review(self, session: Session) -> bool:
        return session in self.sessions_in_review

    def get_session_by_name(self, name: str) -> Session:
        if not self.sessions:
            self.load_data()
        return self.dz_sessions_by_names.get(name.lower(), None)
