import logging

from parladata_base_api.storages.utils import Storage, ParladataObject

logger = logging.getLogger("logger")


class Question(ParladataObject):
    keys = ["gov_id"]

    def __init__(
        self, gov_id: str, id: int, answer_timestamp: str, is_new: bool, parladata_api
    ) -> None:
        self.id = id
        self.gov_id = gov_id
        self.is_new = is_new
        self.answer_timestamp = answer_timestamp
        self.parladata_api = parladata_api

    def update_data(self, data: dict) -> dict:
        question = self.parladata_api.questions.patch(self.id, data)
        self.answer_timestamp = question["answer_timestamp"]
        return question

    def add_answer(self, data: dict) -> dict:
        data.update(question=self.id)
        return self.parladata_api.answers.set(data)


class QuestionStorage(Storage):
    def __init__(self, core_storage) -> None:
        super().__init__(core_storage)
        self.questions = {}
        self.storage = core_storage

    def load_data(self) -> None:
        if not self.questions:
            for question in self.parladata_api.questions.get_all(
                mandate=self.storage.mandate_id
            ):
                self.store_object(question, is_new=False)
            logger.info(f"laoded was {len(self.questions)} questions")

    def store_object(self, question: dict, is_new: bool) -> Question:
        temp_question = Question(
            gov_id=question["gov_id"],
            id=question["id"],
            answer_timestamp=question["answer_timestamp"],
            is_new=is_new,
            parladata_api=self.parladata_api,
        )
        self.questions[temp_question.get_key()] = temp_question
        return temp_question

    def add_or_get_object(self, data: dict) -> Question:
        if not self.questions:
            self.load_data()
        key = Question.get_key_from_dict(data)
        if key in self.questions.keys():
            return self.questions[key]
        else:
            data.update(mandate=self.storage.mandate_id)
            question = self.parladata_api.questions.set(data)
            new_question = self.store_object(question, is_new=True)
            return new_question

    def check_if_question_is_parsed(self, question: dict) -> bool:
        if not self.questions:
            self.load_data()
        key = Question.get_key_from_dict(question)
        return key in self.questions.keys()
