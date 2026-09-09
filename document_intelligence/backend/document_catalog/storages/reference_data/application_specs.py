from typing import Tuple

from document_catalog.dtos.catalog_dtos import ApplicationDTO

UNDER_SCRUTINY = "Under scrutiny"

APPLICATION_SPECS: Tuple[ApplicationDTO, ...] = (
    ApplicationDTO(
        application_id="BN/2026/0421",
        status=UNDER_SCRUTINY,
        field_values={
            "applicantName": "Srinivas Rao Kandula",
            "parentName": "Venkateswara Rao Kandula",
            "dob": "1979-08-14",
            "gender": "Male",
            "aadhaarNo": "731655204821",
            "pan": "DQRPK4831L",
            "mobile": "9849012345",
            "address": "Plot 42, Sri Sai Nagar Colony, Bachupally, Medchal-Malkajgiri 500090",
            "plotNo": "42",
            "surveyNo": "118/2",
            "village": "Bachupally",
            "mandal": "Quthbullapur",
            "district": "Medchal-Malkajgiri",
            "ulb": "Nizampet Municipal Corporation",
            "extentSqYd": "267",
            "proposedUse": "Residential apartment",
            "floors": "Stilt + 4",
            "heightM": "16.5",
            "nearWaterBody": "Yes",
            "roadWidthM": "12",
        },
    ),
    ApplicationDTO(
        application_id="BN/2026/0398",
        status=UNDER_SCRUTINY,
        field_values={
            "applicantName": "Lakshmi Prasanna Devarakonda",
            "parentName": "Ramesh Babu Devarakonda",
            "dob": "1986-02-03",
            "gender": "Female",
            "aadhaarNo": "409322107754",
            "pan": "AKLPD2291Q",
            "mobile": "9908123456",
            "address": "H.No 3-45, Ameenpur, Sangareddy 502032",
            "plotNo": "18",
            "surveyNo": "232/1",
            "village": "Ameenpur",
            "mandal": "Ameenpur",
            "district": "Sangareddy",
            "ulb": "Ameenpur Municipality",
            "extentSqYd": "183",
            "proposedUse": "Individual residential",
            "floors": "Ground + 1",
            "heightM": "7.2",
            "nearWaterBody": "No",
            "roadWidthM": "9",
        },
    ),
    ApplicationDTO(
        application_id="BN/2026/0377",
        status=UNDER_SCRUTINY,
        field_values={
            "applicantName": "Mohammed Irfan Siddiqui",
            "parentName": "Mohammed Yousuf Siddiqui",
            "dob": "1982-11-27",
            "gender": "Male",
            "aadhaarNo": "551809326604",
            "pan": "BNMPS7720K",
            "mobile": "9705456789",
            "address": "H.No 12-2-831/4, Mehdipatnam, Hyderabad 500028",
            "plotNo": "9",
            "surveyNo": "77/2",
            "village": "Kokapet",
            "mandal": "Gandipet",
            "district": "Ranga Reddy",
            "ulb": "Narsingi Municipality",
            "extentSqYd": "420",
            "proposedUse": "Commercial",
            "floors": "Ground + 3",
            "heightM": "14.8",
            "nearWaterBody": "Yes",
            "roadWidthM": "18",
        },
    ),
    # The parcel the shipped deed bundles are written over: Sy. No. 142/2, Plot 17,
    # Kondapur. The 2019 deed in every bundle conveys to this applicant, so the
    # bundle exercises segmentation and chain of title rather than a name mismatch.
    ApplicationDTO(
        application_id="BN/2026/0455",
        status=UNDER_SCRUTINY,
        field_values={
            "applicantName": "Prakash Iyer",
            "parentName": "Subramanian Iyer",
            "dob": "1982-04-19",
            "gender": "Male",
            "aadhaarNo": "628471039265",
            "pan": "AJKPI5510M",
            "mobile": "9885432109",
            "address": "Villa 9, Aparna Cyber Life, Nallagandla, Hyderabad 500019",
            "plotNo": "17",
            "surveyNo": "142/2",
            "village": "Kondapur",
            "mandal": "Serilingampally",
            "district": "Ranga Reddy",
            "ulb": "GHMC Serilingampally Circle",
            "extentSqYd": "400",
            "proposedUse": "Individual residential",
            "floors": "Ground + 2",
            "heightM": "11.4",
            "nearWaterBody": "No",
            "roadWidthM": "9",
        },
    ),
    # The clean happy path over real documents. Every declared value here is what
    # the actual PAN, Aadhaar and driving licence in `samples/identity/` carry, and
    # the departments below hold the same, so a run over those three files reports
    # every check passing.
    #
    # The declared address is the licence address (Kukatpally, Telangana), which is
    # where the applicant lives now. The Aadhaar still carries the permanent
    # Proddatur address, so its address check reports an advisory warning — that
    # disagreement is real and the rule exists to surface it, not to be tuned away.
    ApplicationDTO(
        application_id="BN/2026/0512",
        status=UNDER_SCRUTINY,
        field_values={
            "applicantName": "Chenna Siva Sankar",
            "parentName": "Chenna Chandra Sekhar",
            "dob": "1999-10-28",
            "gender": "Male",
            "aadhaarNo": "255947716541",
            "pan": "NIUPS5913K",
            "mobile": "9848012345",
            "address": "H No 2-45/1, HMT Hills, Kukatpally, Medchal-Malkajgiri 500072",
            "plotNo": "24",
            "surveyNo": "96/3",
            "village": "Kukatpally",
            "mandal": "Balanagar",
            "district": "Medchal-Malkajgiri",
            "ulb": "GHMC Kukatpally Circle",
            "extentSqYd": "300",
            "proposedUse": "Individual residential",
            "floors": "Ground + 2",
            "heightM": "10.5",
            "nearWaterBody": "No",
            "roadWidthM": "10",
        },
    ),
    # The Aadhaar capability showcase (ADR-013). Every declared value here matches
    # the clean synthetic specimen (samples/aadhaar/aadhaar_clean.pdf): the same
    # name, date of birth, gender and Verhoeff-valid Aadhaar number. So the clean
    # specimen reads as fully verified against this application, and the engineered
    # specimens (mismatch, tampered QR, invalid number, poor scan) each fail on the
    # one thing they were built to fail. nearWaterBody stays No and the height under
    # 15 m, so the required-documents checklist asks for identity and title only.
    ApplicationDTO(
        application_id="BN/2026/0601",
        status=UNDER_SCRUTINY,
        field_values={
            "applicantName": "Rithika Sharma",
            "parentName": "Anil Kumar Sharma",
            "dob": "1990-06-15",
            "gender": "Female",
            "aadhaarNo": "234567890124",
            "pan": "AKRPS4416H",
            "mobile": "9866012345",
            "address": (
                "Flat 5B, Lake View Residency, Kondapur, Serilingampally, "
                "Ranga Reddy, Telangana 500084"
            ),
            "plotNo": "12",
            "surveyNo": "142/7",
            "village": "Kondapur",
            "mandal": "Serilingampally",
            "district": "Ranga Reddy",
            "ulb": "GHMC Serilingampally Circle",
            "extentSqYd": "250",
            "proposedUse": "Individual residential",
            "floors": "Ground + 2",
            "heightM": "9.5",
            "nearWaterBody": "No",
            "roadWidthM": "12",
        },
    ),
)
