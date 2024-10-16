from parladata_base_api.storages.utils import ParladataObject, Storage


class Motion(ParladataObject):
    keys = ["text", "datetime"]

    def __init__(
        self,
        id: int,
        text: str,
        title: str,
        session: int,
        datetime: str,
        gov_id: str,
        is_new: bool,
        parladata_api,
        core_storage,
    ) -> None:
        self.id = id
        self.text = text
        self.title = title
        self.session = session
        self.datetime = datetime
        self.gov_id = gov_id
        self.is_new = is_new
        self.vote = None
        self.storage = core_storage
        self.parladata_api = parladata_api

    def patch(self, data: dict) -> dict:
        self.parladata_api.motions.patch(self.id, data)


class Vote(ParladataObject):
    keys = ["name", "timestamp"]

    def __init__(
        self,
        id: int,
        name: str,
        timestamp: str,
        has_anonymous_ballots: bool,
        is_new: bool,
        core_storage,
        parladata_api,
    ) -> None:
        self.id = id
        self.name = name
        self.timestamp = timestamp
        self.has_anonymous_ballots = has_anonymous_ballots
        self.is_new = is_new
        self.storage = core_storage
        self.parladata_api = parladata_api

    def delete_ballots(self):
        self.parladata_api.votes.delete_vote_ballots(self.id)

    def patch(self, data: dict):
        self.parladata_api.votes.patch(self.id, data)


class VoteStorage(Storage):
    def __init__(self, core_storage, session) -> None:
        super().__init__(core_storage)
        self.motions = {}
        self.anonymous_motions = None

        self.session = session

    def load_data(self) -> None:
        votes_by_motion_id = {
            vote["motion"]: vote
            for vote in self.parladata_api.votes.get_all(
                motion__session=self.session.id
            )
        }
        for motion in self.parladata_api.motions.get_all(session=self.session.id):
            temp_motion = self.store_motion(motion, False)
            vote = votes_by_motion_id[temp_motion.id]
            self.store_vote(vote, temp_motion, False)

    def store_motion(self, data: dict, is_new: bool) -> Motion:
        motion = Motion(
            text=data["text"],
            title=data["title"],
            id=data["id"],
            session=data["session"],
            gov_id=data["gov_id"],
            datetime=data["datetime"],
            is_new=is_new,
            core_storage=self.storage,
            parladata_api=self.parladata_api,
        )
        self.motions[motion.get_key()] = motion
        return motion

    def store_vote(self, data: dict, motion: Motion, is_new: bool) -> Vote:
        vote = Vote(
            name=data["name"],
            id=data["id"],
            timestamp=data["timestamp"],
            has_anonymous_ballots=data["has_anonymous_ballots"],
            is_new=is_new,
            core_storage=self.storage,
            parladata_api=self.parladata_api,
        )
        motion.vote = vote
        return vote

    def set_ballots(self, data: dict) -> dict:
        self.parladata_api.ballots.set(data)

    def set_motion(self, data: dict) -> Motion:
        added_motion = self.parladata_api.motions.set(data)
        return self.store_motion(added_motion, True)

    def set_vote(self, data: dict, motion: Motion) -> Vote:
        added_vote = self.parladata_api.votes.set(data)
        return self.store_vote(added_vote, motion, True)

    def get_or_add_object(self, data: dict) -> Motion:
        if not self.motions:
            self.load_data()
        if self.check_if_motion_is_parsed(data):
            key = Motion.get_key_from_dict(data)
            return self.motions[key]
        else:
            motion = self.set_motion(data)
            data["timestamp"] = data["datetime"]
            del data["datetime"]
            data["motion"] = motion.id
            data["name"] = data["title"]
            self.set_vote(data, motion)
            return motion

    def check_if_motion_is_parsed(self, motion: dict) -> bool:
        if not self.motions:
            self.load_data()
        key = Motion.get_key_from_dict(motion)
        return self.motions.get(key, None)
