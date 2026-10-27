# Purpose: Preserve the deferred checker import in already-running production jobs.
# The implementation lives in validation_tools; retain this bridge until those jobs finish.
from validation_tools.audit_native import audit
