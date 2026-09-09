CLASSIFY_PROMPT = """These images are the pages of ONE uploaded Indian document, in order.

Decide which document type it is. Choose the id from this list and return nothing else:
{document_type_options}

If the pages do not match any type in the list, or you cannot tell, return the id 'unknown'.
Judge from the layout, the issuing authority named on it, and the fields printed on it — not from
any filename. Report your confidence in the choice between 0 and 1."""
