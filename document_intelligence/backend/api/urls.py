from django.urls import path

from api.views import (
    analyze_views,
    catalog_views,
    demo_sample_views,
    officer_action_views,
    thread_views,
)

urlpatterns = [
    path("catalog", catalog_views.get_document_catalog, name="get_document_catalog"),
    path("applications", catalog_views.get_applications, name="get_applications"),
    path(
        "demo/aadhaar-specimens",
        demo_sample_views.list_aadhaar_specimens,
        name="list_aadhaar_specimens",
    ),
    path(
        "demo/aadhaar-specimens/<str:filename>",
        demo_sample_views.get_aadhaar_specimen,
        name="get_aadhaar_specimen",
    ),
    path("threads", thread_views.create_scrutiny_thread, name="create_scrutiny_thread"),
    path(
        "threads/<str:thread_id>",
        thread_views.get_scrutiny_thread,
        name="get_scrutiny_thread",
    ),
    path(
        "threads/<str:thread_id>/documents",
        thread_views.add_documents,
        name="add_documents",
    ),
    path(
        "threads/<str:thread_id>/analyze",
        analyze_views.stream_thread_analysis,
        name="stream_thread_analysis",
    ),
    path(
        "threads/<str:thread_id>/documents/<str:document_id>/fields/<str:field_key>",
        officer_action_views.update_document_field,
        name="update_document_field",
    ),
    path(
        "threads/<str:thread_id>/documents/<str:document_id>/confirm",
        officer_action_views.confirm_document_fields,
        name="confirm_document_fields",
    ),
    path(
        "threads/<str:thread_id>/documents/<str:document_id>/retry-verification",
        officer_action_views.retry_issuer_verification,
        name="retry_issuer_verification",
    ),
    path(
        "threads/<str:thread_id>/checks/<str:check_id>/resolve",
        officer_action_views.resolve_check,
        name="resolve_check",
    ),
    path(
        "threads/<str:thread_id>/service-overrides",
        officer_action_views.update_service_overrides,
        name="update_service_overrides",
    ),
    path(
        "threads/<str:thread_id>/note",
        officer_action_views.get_scrutiny_note,
        name="get_scrutiny_note",
    ),
]
