# AI Readiness Gate

This gate is enforced via the `/ai-readiness-check` skill. Dhruva invokes it when new apps (`apps.py` added / `INSTALLED_APPS` changed) or new significant modules (new interactor subpackage, `jobs/`, `tasks/`, configio module, `adapters/`, `event_handlers/`) appear in the diff.
