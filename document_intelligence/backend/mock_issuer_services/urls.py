from django.urls import path

from mock_issuer_services.views import (
    igrs_deed_views,
    itd_pan_views,
    sarathi_licence_views,
    uidai_aadhaar_views,
)

urlpatterns = [
    path("itd/pan/verify", itd_pan_views.verify_pan, name="mock_itd_verify_pan"),
    path(
        "uidai/aadhaar/verify",
        uidai_aadhaar_views.verify_aadhaar,
        name="mock_uidai_verify_aadhaar",
    ),
    path(
        "sarathi/dl/<str:licence_number>",
        sarathi_licence_views.look_up_licence,
        name="mock_sarathi_look_up_licence",
    ),
    # A registration number carries a slash, so the whole rest of the path is taken
    # as the document number rather than matched segment by segment.
    path(
        "igrs/deeds/<path:doc_no>",
        igrs_deed_views.look_up_deed,
        name="mock_igrs_look_up_deed",
    ),
]
