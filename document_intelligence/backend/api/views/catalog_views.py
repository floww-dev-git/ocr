from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from document_catalog.interactors.get_applications_interactor import (
    GetApplicationsInteractor,
)
from document_catalog.interactors.get_document_catalog_interactor import (
    GetDocumentCatalogInteractor,
)
from document_catalog.presenters.catalog_presenter import CatalogPresenter
from document_catalog.storages.in_memory_application_storage import (
    InMemoryApplicationStorage,
)
from document_catalog.storages.in_memory_catalog_storage import InMemoryCatalogStorage


@require_GET
def get_document_catalog(request: HttpRequest) -> JsonResponse:
    interactor = GetDocumentCatalogInteractor(
        catalog_storage=InMemoryCatalogStorage(),
        application_storage=InMemoryApplicationStorage(),
    )
    catalog = interactor.get_document_catalog()
    response = CatalogPresenter().get_document_catalog_response(catalog=catalog)
    return JsonResponse(response)


@require_GET
def get_applications(request: HttpRequest) -> JsonResponse:
    interactor = GetApplicationsInteractor(application_storage=InMemoryApplicationStorage())
    applications = interactor.get_applications()
    response = CatalogPresenter().get_applications_response(applications=applications)
    return JsonResponse(response)
