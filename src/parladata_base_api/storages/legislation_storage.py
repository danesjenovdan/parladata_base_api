import logging

from parladata_base_api.storages.utils import ParladataObject, Storage

logger = logging.getLogger("logger")


class Law(ParladataObject):
    keys = ["epa", "mandate"]

    def __init__(
        self, id, epa, text, status, timestamp, uid, classification, mandate, is_new
    ) -> None:
        self.id = id
        self.epa = epa
        self.text = text
        self.status = status
        self.classification = classification
        self.timestamp = timestamp
        self.uid = uid
        self.mandate = mandate
        self.considerations = []
        self.is_new = is_new

    def get_timestamp_of_latest_consideration(self) -> str:
        if not self.considerations:
            return None
        return max([consideration.timestamp for consideration in self.considerations])


class ProcedurePhase(ParladataObject):
    keys = ["name"]

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name


class LegislationStatuses(ParladataObject):
    keys = ["name"]

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name

    @classmethod
    def get_obj(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
        }


class LegislationClassification(ParladataObject):
    keys = ["name"]

    def __init__(self, id, name) -> None:
        self.id = id
        self.name = name


class LegislationConsideration(ParladataObject):
    keys = ["legislation", "session"]

    def __init__(self, id, law, timestamp, procedure_phase, session, is_new) -> None:
        self.id = id
        self.legislation = law
        self.timestamp = timestamp
        self.procedure_phase = procedure_phase
        self.session = session
        self.is_new = is_new


class LegislationStorage(Storage):
    def __init__(self, code_storage) -> None:
        super().__init__(code_storage)

        self.legislation = {}
        self.legislation_by_id = {}
        self.statuses_by_id = {None: None}
        self.legislation_classifications = {}
        self.legislation_statuses = {}
        self.procedure_phases = {}
        self.procedure_phases_by_id = {}
        self.legislation_considerations = {}

    def load_data(self) -> None:
        """
        load legislation if not loaded
        """
        if self.legislation:
            return
        logger.debug("Load legislation")
        for (
            legislation_classification
        ) in self.parladata_api.legislation_classifications.get_all():
            classification = LegislationClassification(
                id=legislation_classification["id"],
                name=legislation_classification["name"],
            )
            self.legislation_classifications[classification.get_key()] = classification

        for procedure_phase in self.parladata_api.procedure_phases.get_all():
            procedure_phase_obj = ProcedurePhase(
                id=procedure_phase["id"], name=procedure_phase["name"]
            )
            self.procedure_phases[procedure_phase_obj.get_key()] = procedure_phase_obj
            self.procedure_phases_by_id[procedure_phase_obj.id] = procedure_phase_obj

        for legislation_status in self.parladata_api.legislation_statuses.get_all():
            status = LegislationStatuses(
                id=legislation_status["id"], name=legislation_status["name"]
            )
            self.statuses_by_id[legislation_status["id"]] = status
            self.legislation_statuses[status.get_key()] = status

        for law in self.parladata_api.legislation.get_all(
            mandate=self.storage.mandate_id
        ):
            self.store_object(law, is_new=False)

        # TODO thik about optimizations per session
        for (
            legislation_consideration
        ) in self.parladata_api.legislation_consideration.get_all(
            legislation__mandate=self.storage.mandate_id
        ):
            self.store_legislation_consideration(
                legislation_consideration, is_new=False
            )

    def store_object(self, law_dict, is_new) -> Law:
        if "status" in law_dict.keys():
            status = self.statuses_by_id[law_dict["status"]]
        else:
            status = self.legislation_statuses["in_procedure"]

        law_obj = Law(
            id=law_dict["id"],
            epa=law_dict["epa"],
            text=law_dict["text"],
            status=status,
            timestamp=law_dict["timestamp"],
            classification=law_dict.get("classification", None),
            uid=law_dict["uid"],
            mandate=law_dict["mandate"],
            is_new=is_new,
        )
        self.legislation[law_obj.get_key()] = law_obj
        self.legislation_by_id[law_obj.id] = law_obj
        return law_obj

    def set_law_status(self, law, status_name) -> Law:
        status = self.legislation_statuses[status_name]
        data = {"status": status.id}
        patched_law = self.parladata_api.legislation.patch(law.id, data)
        return self.store_object(patched_law, is_new=False)

    def set_law_as_enacted(self, epa) -> None:
        in_procedure = self.legislation_statuses["in_procedure"]
        enacted = self.legislation_statuses["enacted"]
        key = self.get_key_from_epa(epa)
        if key in self.legislation.keys():
            law = self.legislation[key]
            if law.status == in_procedure or law.status == None:
                # update status
                data = {"status": enacted.id}
                patched_law = self.parladata_api.legislation.patch(law.id, data)
                self.store_object(patched_law, is_new=False)

    def set_law_as_rejected(self, epa) -> None:
        in_procedure = self.legislation_statuses["in_procedure"]
        rejected = self.legislation_statuses["rejected"]
        key = self.get_key_from_epa(epa)
        if key in self.legislation.keys():
            law = self.legislation[key]
            if law.status == in_procedure or law.status == None:
                # update status
                data = {"status": rejected.id}
                patched_law = self.parladata_api.legislation.patch(law.id, data)
                self.store_object(patched_law, is_new=False)

    def set_law_as_in_procedure(self, epa) -> None:
        in_procedure = self.legislation_statuses["in_procedure"]
        key = self.get_key_from_epa(epa)
        if key in self.legislation.keys():
            law = self.legislation[key]
            # update status
            data = {"status": in_procedure.id}
            patched_law = self.parladata_api.legislation.patch(law.id, data)
            self.store_object(patched_law, is_new=False)

    def store_legislation_consideration(
        self, consideration_dict, is_new
    ) -> LegislationConsideration:
        law = self.legislation_by_id[consideration_dict["legislation"]]
        phase = self.procedure_phases_by_id[consideration_dict["procedure_phase"]]
        consideration = LegislationConsideration(
            id=consideration_dict["id"],
            law=law,
            timestamp=consideration_dict["timestamp"],
            procedure_phase=phase,
            session=consideration_dict["session"],
            is_new=is_new,
        )
        law.considerations.append(consideration)
        self.legislation_considerations[consideration.get_key()] = consideration
        return consideration

    def set_law(self, data) -> Law:
        added_law = self.parladata_api.legislation.set(data)
        law_obj = self.store_object(added_law, is_new=True)
        return law_obj

    def get_law(self, epa) -> Law:
        if not self.legislation_statuses:
            self.load_data()
        return self.legislation.get(epa, None)

    def set_legislation_consideration(self, data) -> LegislationConsideration:
        legislation_consideration = self.parladata_api.legislation_consideration.set(
            data
        )
        legislation_consideration = self.store_legislation_consideration(
            legislation_consideration, is_new=True
        )
        return legislation_consideration

    def patch_law(self, law, data) -> Law:
        patched_law = self.parladata_api.legislation.patch(law.id, data)
        law_obj = self.store_object(patched_law, is_new=False)
        return law_obj

    def get_key_from_epa(self, epa) -> str:
        key = Law.get_key_from_dict({"epa": epa, "mandate": self.storage.mandate_id})
        return key

    def is_law_parsed(self, epa) -> bool:
        if not self.legislation_statuses:
            self.load_data()
        key = self.get_key_from_epa(epa)
        return key in self.legislation.keys()

    def has_law_name(self, epa) -> bool:
        if not self.legislation_statuses:
            self.load_data()
        return epa in self.legislation.keys()

    def get_law_by_epa(self, epa) -> Law:
        if not self.legislation_statuses:
            self.load_data()
        key = self.get_key_from_epa(epa)
        return self.legislation.get(key, None)

    def get_or_add_object(self, law_data) -> object:
        if not self.legislation_statuses:
            self.load_data()
        key = Law.get_key_from_dict(law_data)

        if key in self.legislation.keys():
            return self.legislation[key]
        else:
            law = self.set_law(law_data)
        return law

    def update_or_add_law(self, law_data) -> Law:
        if not self.legislation_statuses:
            self.load_data()
        key = Law.get_key_from_dict(law_data)

        if key in self.legislation.keys():
            law = self.legislation[key]
            if law.text == None or law.text == "" or law.classification == None:
                law = self.patch_law(law, law_data)
        else:
            law = self.set_law(law_data)
        return law

    def get_legislation_status_by_name(self, name) -> int:
        if not self.legislation_statuses:
            self.load_data()
        return self.legislation_statuses[name].id

    def prepare_and_set_legislation_consideration(
        self, legislation_consideration
    ) -> LegislationConsideration:
        legislation_consideration_key = LegislationConsideration.get_key_from_dict(
            legislation_consideration
        )
        if not legislation_consideration_key in self.legislation_considerations.keys():
            legislation_consideration = self.set_legislation_consideration(
                legislation_consideration
            )
        else:
            legislation_consideration = self.legislation_considerations[
                legislation_consideration_key
            ]
        return legislation_consideration

    def get_procedure_phase(self, procedure_phase: dict) -> ProcedurePhase:
        key = ProcedurePhase.get_key_from_dict(procedure_phase)
        if not self.procedure_phases:
            self.load_data()
        return self.procedure_phases.get(key, None)

    def get_legislation_classifications_by_name(self, name) -> int:
        if not self.legislation_statuses:
            self.load_data()
        key = LegislationClassification.get_key_from_dict({"name": name})
        try:
            legislation_classifications = self.legislation_classifications.get(key)
        except:
            print(f"name is not in loaded legislation classifications")
            return
        return legislation_classifications.id
