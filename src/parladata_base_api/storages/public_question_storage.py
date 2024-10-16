import logging

from parladata_base_api.storages.utils import ParladataObject, Storage

logger = logging.getLogger("logger")


class PublicQuestion(ParladataObject):
    keys = ["gov_id"]

    def __init__(self, gov_id: str, id: int, is_new: bool) -> None:
        self.id = id
        self.gov_id = gov_id
        self.is_new = is_new


class PublicAnswer(ParladataObject):
    keys = ["gov_id"]

    def __init__(self, gov_id: str, id: int, is_new: bool) -> None:
        self.id = id
        self.gov_id = gov_id
        self.is_new = is_new


class PublicQuestionStorage(Storage):
    def __init__(self, core_storage) -> None:
        super().__init__(core_storage)
        self.public_questions = {}
        self.public_answers = {}

    def load_data(self) -> None:
        if not self.public_questions:
            for public_question in self.parladata_api.public_person_questions.get_all(
                mandate=self.storage.mandate_id
            ):
                self.store_public_question(public_question, False)
            logger.info(f"laoded was {len(self.public_questions)} public questions")
        if not self.public_answers:
            for public_answer in self.parladata_api.public_person_answers.get_all(
                mandate=self.storage.mandate_id
            ):
                self.store_public_answer(public_answer, False)
            logger.info(f"laoded was {len(self.public_answers)} public answers")

    def store_public_question(
        self, public_question: dict, is_new: bool
    ) -> PublicQuestion:
        temp_question = PublicQuestion(
            gov_id=public_question["gov_id"],
            id=public_question["id"],
            is_new=is_new,
        )
        self.public_questions[temp_question.get_key()] = temp_question
        return temp_question

    def store_public_answer(self, public_answer: dict, is_new: bool) -> PublicAnswer:
        temp_answer = PublicQuestion(
            gov_id=public_answer["gov_id"],
            id=public_answer["id"],
            is_new=is_new,
        )
        self.public_answers[temp_answer.get_key()] = temp_answer
        return temp_answer

    def set_public_question(self, data: dict) -> PublicQuestion:
        if not self.public_questions:
            self.load_data()
        added_question = self.parladata_api.public_person_questions.set(data)
        self.store_public_question(added_question, True)
        return added_question

    def check_if_public_question_is_parsed(self, question: dict) -> bool:
        if not self.public_questions:
            self.load_data()
        key = PublicQuestion.get_key_from_dict(question)
        return key in self.public_questions.keys()

    def get_public_question(self, gov_id: str) -> PublicQuestion:
        if not self.public_questions:
            self.load_data()
        return self.public_questions[gov_id]

    def set_public_answer(self, data: dict) -> PublicAnswer:
        if not self.public_answers:
            self.load_data()
        added_answer = self.parladata_api.public_person_answers.set(data)
        self.store_public_answer(added_answer, True)
        return added_answer

    def check_if_public_answer_is_parsed(self, answer: dict) -> bool:
        if not self.public_answers:
            self.load_data()
        key = PublicAnswer.get_key_from_dict(answer)
        return key in self.public_answers.keys()
