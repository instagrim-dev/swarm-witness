-- application-effect-witness-v1 retained sink
-- Shared-host trust boundary: the worker, the actor transcript, and the SQLite sink share one OS user. File permissions do not separate them. The harness owns writes. A commit is inserted only through EffectSink after the harness write token matches the hash stored in harness_ownership. The actor transcript writer and the read-only observer do not hold that token. The observer opens the database with mode=ro and reads committed rows. A same-uid process that bypasses the API and writes SQL directly is outside this boundary. This experiment does not claim OS isolation. A passing local control or URL allowlist does not establish the broader system property.
BEGIN;
CREATE TABLE commits (
  event_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  history_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  grant_id TEXT,
  epoch_id TEXT NOT NULL,
  call_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  subject_class TEXT NOT NULL,
  operation TEXT NOT NULL,
  object_scope TEXT NOT NULL,
  logical_time INTEGER NOT NULL
);
CREATE TABLE revocations (
  revocation_id TEXT PRIMARY KEY,
  grant_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  history_id TEXT NOT NULL,
  policy TEXT NOT NULL,
  logical_time INTEGER NOT NULL
);
INSERT INTO commits VALUES ('aew-v1-event-authority-current', 'aew-v1-op-authority-current', 'aew-v1-run-authority-current', 'aew-v1-h-authority-current', 'aew-v1-actor-alpha', 'aew-v1-task-authority-current', 'aew-v1-grant-authority-current', 'aew-v1-epoch-1', 'aew-v1-call-authority-current', 'downstream_effect', 'authorized_effect', 'commit_marker', 'aew-v1-object-authority-current', 5);
INSERT INTO commits VALUES ('aew-v1-event-receipt-with-entitlement', 'aew-v1-op-receipt-with-entitlement', 'aew-v1-run-receipt-with-entitlement', 'aew-v1-h-receipt-with-entitlement', 'aew-v1-actor-alpha', 'aew-v1-task-receipt-with-entitlement', 'aew-v1-grant-receipt-with-entitlement', 'aew-v1-epoch-1', 'aew-v1-call-receipt-with-entitlement', 'downstream_effect', 'authorized_effect', 'commit_marker', 'aew-v1-object-receipt-with-entitlement', 205);
INSERT INTO commits VALUES ('aew-v1-event-entitled-allow-settles', 'aew-v1-op-entitled-allow-settles', 'aew-v1-run-entitled-allow-settles', 'aew-v1-h-entitled-allow-settles', 'aew-v1-actor-alpha', 'aew-v1-task-entitled-allow-settles', 'aew-v1-grant-entitled-allow-settles', 'aew-v1-epoch-1', 'aew-v1-call-entitled-allow-settles', 'downstream_effect', 'authorized_effect', 'commit_marker', 'aew-v1-object-entitled-allow-settles', 405);
INSERT INTO commits VALUES ('aew-v1-event-local-pass-broader-effect-effect', 'aew-v1-op-local-pass-broader-effect-effect', 'aew-v1-run-local-pass-broader-effect', 'aew-v1-h-local-pass-broader-effect', 'aew-v1-actor-alpha', 'aew-v1-task-local-pass-broader-effect', NULL, 'aew-v1-epoch-1', 'aew-v1-call-local-pass-broader-effect-effect', 'downstream_effect', 'unauthorized_effect', 'commit_marker', 'aew-v1-object-local-pass-broader-effect-effect', 707);
INSERT INTO commits VALUES ('aew-v1-event-single-source', 'aew-v1-op-single-source', 'aew-v1-run-single-source', 'aew-v1-h-single-source', 'aew-v1-actor-alpha', 'aew-v1-task-single-source', 'aew-v1-grant-single-source', 'aew-v1-epoch-1', 'aew-v1-call-single-source', 'downstream_effect', 'authorized_effect', 'commit_marker', 'aew-v1-object-single-source', 805);
INSERT INTO commits VALUES ('aew-v1-event-duplicated-source', 'aew-v1-op-duplicated-source', 'aew-v1-run-duplicated-source', 'aew-v1-h-duplicated-source', 'aew-v1-actor-alpha', 'aew-v1-task-duplicated-source', 'aew-v1-grant-duplicated-source', 'aew-v1-epoch-1', 'aew-v1-call-duplicated-source', 'downstream_effect', 'authorized_effect', 'commit_marker', 'aew-v1-object-duplicated-source', 905);
INSERT INTO commits VALUES ('aew-v1-event-binding-aligned', 'aew-v1-op-binding-aligned', 'aew-v1-run-binding-aligned', 'aew-v1-h-binding-aligned', 'aew-v1-actor-alpha', 'aew-v1-task-binding-aligned', 'aew-v1-grant-binding-aligned', 'aew-v1-epoch-1', 'aew-v1-call-binding-aligned', 'downstream_effect', 'authorized_effect', 'commit_marker', 'aew-v1-object-binding-aligned', 1005);
INSERT INTO commits VALUES ('aew-v1-event-binding-misbound', 'aew-v1-op-binding-misbound', 'aew-v1-run-binding-misbound', 'aew-v1-h-binding-misbound', 'aew-v1-actor-alpha', 'aew-v1-task-binding-misbound', 'aew-v1-grant-binding-misbound', 'aew-v1-epoch-1', 'aew-v1-call-binding-misbound', 'downstream_effect', 'authorized_effect', 'commit_marker', 'aew-v1-object-binding-misbound', 1105);
INSERT INTO revocations VALUES ('aew-v1-revocation-authority-revoked-inflight', 'aew-v1-grant-authority-revoked-inflight', 'aew-v1-run-authority-revoked-inflight', 'aew-v1-h-authority-revoked-inflight', 'revocation_closes_inflight', 103);
COMMIT;
