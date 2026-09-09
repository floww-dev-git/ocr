from typing import Dict, List

from document_catalog.dtos.catalog_dtos import ApplicationDTO, ApplicationFieldSpecDTO
from document_catalog.exceptions.catalog_exceptions import ApplicationNotFound
from document_catalog.storage_interfaces.application_storage_interface import (
    ApplicationStorageInterface,
)
from document_catalog.storages.reference_data.application_field_specs import (
    APPLICATION_FIELD_SPECS,
)
from document_catalog.storages.reference_data.application_specs import APPLICATION_SPECS


class InMemoryApplicationStorage(ApplicationStorageInterface):
    def get_applications(self) -> List[ApplicationDTO]:
        return [self._prep_application_dto(spec) for spec in APPLICATION_SPECS]

    def get_application(self, application_id: str) -> ApplicationDTO:
        application = self._applications_by_id().get(application_id)
        if application is None:
            raise ApplicationNotFound(application_id=application_id)
        return self._prep_application_dto(application)

    def get_application_field_specs(self) -> List[ApplicationFieldSpecDTO]:
        return list(APPLICATION_FIELD_SPECS)

    @staticmethod
    def _applications_by_id() -> Dict[str, ApplicationDTO]:
        return {application.application_id: application for application in APPLICATION_SPECS}

    @staticmethod
    def _prep_application_dto(application: ApplicationDTO) -> ApplicationDTO:
        return ApplicationDTO(
            application_id=application.application_id,
            status=application.status,
            field_values=dict(application.field_values),
        )
