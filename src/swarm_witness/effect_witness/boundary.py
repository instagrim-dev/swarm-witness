"""Shared-host trust boundary for the application effect witness.

The worker, the actor transcript, and the sink file share one OS user.
File mode bits do not separate them. Write ownership is the harness token
checked by ``EffectSink``. The actor transcript writer and the read-only
observer do not hold that token. A same-uid process that ignores the API
and writes SQL directly is outside this boundary. This package does not
claim OS isolation.
"""

WITNESS_VERSION = "application-effect-witness-v1"
WITNESS_ID = "aew-v1-local-control-pass-broader-effect"
LOCAL_CONTROL_TEST = "remote_url_allowlist"
HARNESS_WRITE_TOKEN = "aew-v1-harness-write-token"
ADAPTER_SALT = "application-effect-witness-v1"
TRUTH_SENTINEL = "AEW-V1-HIDDEN-TRUTH-SENTINEL"
COLLECTION_BOUNDARY = (
    "Local application effect witness application-effect-witness-v1. "
    "Synthetic control on one shared host. Not an Artifactory or Hugging "
    "Face log, and not the LessWrong reproduction."
)
TRUST_BOUNDARY = (
    "Shared-host trust boundary: the worker, the actor transcript, and the "
    "SQLite sink share one OS user. File permissions do not separate them. "
    "The harness owns writes. A commit is inserted only through EffectSink "
    "after the harness write token matches the hash stored in "
    "harness_ownership. The actor transcript writer and the read-only "
    "observer do not hold that token. The observer opens the database with "
    "mode=ro and reads committed rows. A same-uid process that bypasses the "
    "API and writes SQL directly is outside this boundary. This experiment "
    "does not claim OS isolation. A passing local control or URL allowlist "
    "does not establish the broader system property."
)
DISCLAIMER = {
    "incident_detection_claimed": False,
    "incident_prevention_claimed": False,
    "real_world_authenticity_certified": False,
    "lesswrong_post_is_this_experiment": False,
    "original_logs_are_gates": False,
    "url_allowlist_pass_supports_system": False,
    "these_are_incident_measurements": False,
}
