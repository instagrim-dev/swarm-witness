//go:build swarm_witness_r3

package sessioncompaction

// Companion fixture hooks for the disposable-tree bridge.
//
// Seeds synthetic owner-witness state extracted from
// ordinary_retry_retained_grant_owner_witness_test.go at pin
// 4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe, then drives
// ClaimOrdinaryRetainedGrantFirstEditTx for protocol actions.
//
// Protocol-level identities (task-alpha, grant-alpha, …) stay in observation
// inputs/state projections; native receipts use real BMO task/owner values.
// Spent status comes from authoritative transfer/claim readback.

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"

	"github.com/instagrim-dev/bmo/internal/agent/bridge"
	"github.com/instagrim-dev/bmo/internal/bmoi/runloop"
	bmoitools "github.com/instagrim-dev/bmo/internal/bmoi/tools"
	"github.com/instagrim-dev/bmo/internal/db"
	"github.com/instagrim-dev/bmo/internal/ingresslineage"
	"github.com/instagrim-dev/bmo/internal/lifecycleprovenance"
	"github.com/instagrim-dev/bmo/internal/message"
	"github.com/instagrim-dev/bmo/internal/runevents"
	"github.com/instagrim-dev/bmo/internal/runtimeevidence"
	"github.com/instagrim-dev/bmo/internal/runtimeevidence/ordinaryrepair"
	"github.com/instagrim-dev/bmo/internal/sessionfence"
	"github.com/instagrim-dev/bmo/internal/taskcheckout"
)

func init() {
	swarmWitnessR3FixtureReady = func() bool { return true }
	swarmWitnessR3OpenCase = openSwarmWitnessR3Case
	swarmWitnessR3Apply = applySwarmWitnessR3
}

type swarmWitnessR3Handle struct {
	dbPath     string
	conn       *sql.DB
	release    func()
	owned      context.Context
	carried    context.Context
	admissions *AdmissionStore
	epoch      OrdinaryRetryEpoch
	snapshot   AdmissionOwnerSnapshot
	binding    taskcheckout.Binding
	root       string
	path       string
	files      map[string]string
	workspace  string
	pre        string
	post       string
	hint       runloop.DiagnosticDeliveredSourcePathHint
	fixture    probeCaseFixture
	taskID     string
}

type swarmWitnessR3Sidecar struct {
	Root      string            `json:"root"`
	Path      string            `json:"path"`
	Files     map[string]string `json:"files"`
	Workspace string            `json:"workspace"`
	Pre       string            `json:"pre"`
	Post      string            `json:"post"`
	Fixture   probeCaseFixture  `json:"fixture"`
}

func sidecarPath(dbPath string) string {
	return dbPath + ".r3.json"
}

func openSwarmWitnessR3Case(ctx context.Context, dbPath string, fixture probeCaseFixture) (any, func(), error) {
	_ = os.Setenv(lifecycleprovenance.EnvironmentKey, "retained-grant-owner-witness")
	if err := os.MkdirAll(filepath.Dir(dbPath), 0o755); err != nil {
		return nil, func() {}, err
	}
	// Each case uses a fresh dbPath; reopen cycles the connection in-place.
	h, err := seedSwarmWitnessR3(ctx, dbPath, fixture)
	if err != nil {
		return nil, func() {}, err
	}
	return h, h.cleanup, nil
}

func (h *swarmWitnessR3Handle) cleanup() {
	if h.release != nil {
		h.release()
		h.release = nil
	}
	if h.conn != nil {
		_ = h.conn.Close()
		h.conn = nil
	}
}

func applySwarmWitnessR3(ctx context.Context, store any, cse probeCase, act probeCaseAction) (stepObservation, error) {
	h, ok := store.(*swarmWitnessR3Handle)
	if !ok || h == nil {
		return unsupportedObs(cse, act, "bad_handle"), fmt.Errorf("bad handle")
	}
	switch act.Op {
	case "reopen":
		if err := h.reopen(ctx); err != nil {
			return failedObs(cse, act, err), err
		}
		state, err := h.projectState()
		if err != nil {
			return failedObs(cse, act, err), err
		}
		return stepObservation{
			ProtocolID:      "r3-ledger-claim-v1",
			CaseID:          cse.CaseID,
			Step:            act.Step,
			Op:              "reopen",
			AdapterID:       "bmo_l1_first_edit",
			ExecutionStatus: "completed",
			Disposition:     "observed",
			Inputs:          map[string]any{},
			NativeResult:    map[string]any{"reopened": true, "native_bmo": true},
			State:           state,
			Notes:           "cold database reopen",
		}, nil
	case "inspect":
		state, err := h.projectState()
		if err != nil {
			return failedObs(cse, act, err), err
		}
		return stepObservation{
			ProtocolID:      "r3-ledger-claim-v1",
			CaseID:          cse.CaseID,
			Step:            act.Step,
			Op:              "inspect",
			AdapterID:       "bmo_l1_first_edit",
			ExecutionStatus: "completed",
			Disposition:     "observed",
			Inputs:          map[string]any{},
			NativeResult:    map[string]any{"native_bmo": true},
			State:           state,
			Notes:           "",
		}, nil
	case "claim_first_edit":
		return h.claimFirstEdit(ctx, cse, act)
	default:
		return unsupportedObs(cse, act, "unknown_op"), fmt.Errorf("unknown op %q", act.Op)
	}
}

func (h *swarmWitnessR3Handle) claimFirstEdit(ctx context.Context, cse probeCase, act probeCaseAction) (stepObservation, error) {
	txCompletion := act.TransactionCompletion
	if txCompletion == "" {
		txCompletion = "commit"
	}
	inputs := actionInputs(act)
	receipt, err := h.buildReceipt(act)
	if err != nil {
		return failedObs(cse, act, err), err
	}
	tx, err := h.conn.BeginTx(h.carried, nil)
	if err != nil {
		return failedObs(cse, act, err), err
	}
	claimErr := h.admissions.ClaimOrdinaryRetainedGrantFirstEditTx(h.carried, tx, h.epoch, receipt)
	nativeOK := claimErr == nil
	disposition := "refused"
	reason := ""
	if claimErr != nil {
		reason = claimErr.Error()
		_ = tx.Rollback()
	} else if txCompletion == "rollback_after_native_success" {
		_ = tx.Rollback()
		disposition = "rolled_back"
		reason = "rollback_after_native_success"
	} else {
		if err := tx.Commit(); err != nil {
			_ = tx.Rollback()
			return failedObs(cse, act, err), err
		}
		disposition = "committed"
		reason = "ok"
	}
	state, err := h.projectState()
	if err != nil {
		return failedObs(cse, act, err), err
	}
	return stepObservation{
		ProtocolID:      "r3-ledger-claim-v1",
		CaseID:          cse.CaseID,
		Step:            act.Step,
		Op:              "claim_first_edit",
		AdapterID:       "bmo_l1_first_edit",
		ExecutionStatus: "completed",
		Disposition:     disposition,
		Inputs:          inputs,
		NativeResult: map[string]any{
			"native_bmo": true,
			"native_ok":  nativeOK,
			"reason":     reason,
			"call_id":    act.CallID,
		},
		State: state,
		Notes: reason,
	}, nil
}

func (h *swarmWitnessR3Handle) buildReceipt(act probeCaseAction) (OrdinaryRetryFirstEditReceipt, error) {
	input := `{"file_path":"answer.go","new_string":"new","old_string":"old"}`
	r := OrdinaryRetryFirstEditReceipt{
		EpochDigest:        OrdinaryRetryEpochDigest(h.epoch),
		RetryRunID:         h.epoch.RetryRunID,
		TaskID:             h.epoch.TaskID,
		CheckoutRoot:       h.root,
		WorkspaceSHA256:    h.workspace,
		SourceSHA256:       h.files,
		CallID:             act.CallID,
		InputSHA256:        sha256Hex([]byte(input)),
		TargetPath:         h.path,
		TargetBeforeSHA256: h.post,
		TargetAfterSHA256:  strings.Repeat("3", 64),
		OwnerRevision:      h.snapshot.Revision,
		OwnerDigest:        h.snapshot.Digest,
		BudgetLimit:        10,
		BudgetUsed:         5,
		ViewHint:           h.hint,
	}
	// Drive native refusal paths from protocol action identity mismatches.
	// Keep receipt TaskID / OwnerRevision on the durable epoch+snapshot
	// identities (h.epoch.TaskID, h.snapshot.*). Synthetic classical aliases
	// such as "task-alpha" must not overwrite native admission digests.
	if act.TaskID != "" && act.TaskID != h.fixture.TaskID {
		r.TaskID = "foreign"
	}
	if act.OwnerRevision != 0 && int64(act.OwnerRevision) != h.fixture.OwnerRevision {
		r.OwnerRevision = int64(act.OwnerRevision)
	}
	if act.OwnerRevision == 0 && h.fixture.OwnerRevision != 0 {
		// Protocol uses 0 as stale/noncurrent revision.
		r.OwnerRevision = 0
		r.OwnerDigest = ""
	}
	// Grant / epoch mismatches are observed via durable transfer rows in
	// projectState and by protocol input pairing — not by inventing receipt
	// fields BMO omits. Cross-arm equality uses call_id/spent/counts only.
	d, err := OrdinaryRetryFirstEditDigest(r)
	if err != nil {
		return OrdinaryRetryFirstEditReceipt{}, err
	}
	r.Attestation = lifecycleprovenance.AttestDigest("ordinary-retry-first-edit/v1:" + d)
	return r, nil
}

func (h *swarmWitnessR3Handle) projectState() (map[string]any, error) {
	var transferCount int
	if err := h.conn.QueryRowContext(h.carried, `SELECT COUNT(*) FROM ordinary_retry_retained_grant_transfers WHERE session_id=?`, h.epoch.SessionID).Scan(&transferCount); err != nil {
		return nil, err
	}
	// Read durable first-edit receipts; identity fields come from receipt JSON
	// (observed), with explicit alias notes when a field is absent from SQLite.
	rows, err := h.conn.QueryContext(h.carried, `SELECT call_id, receipt_json FROM ordinary_retry_first_edits WHERE session_id=? AND generation=? ORDER BY call_id`, h.epoch.SessionID, h.epoch.Generation)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	claims := make([]map[string]any, 0)
	callIDs := make([]string, 0)
	for rows.Next() {
		var id, receiptRaw string
		if err := rows.Scan(&id, &receiptRaw); err != nil {
			return nil, err
		}
		callIDs = append(callIDs, id)
		taskID := ""
		var ownerRev any = nil
		var parsed map[string]any
		if json.Unmarshal([]byte(receiptRaw), &parsed) == nil {
			if v, ok := parsed["task_id"].(string); ok {
				taskID = v
			}
			if v, ok := parsed["owner_revision"].(float64); ok {
				ownerRev = int64(v)
			}
		}
		// grant_id / retry_epoch are not columns on ordinary_retry_first_edits;
		// alias from the live epoch/admission only when the durable transfer row
		// has not yet been written, and mark the alias explicitly.
		rec := map[string]any{
			"call_id":                id,
			"task_id":                taskID,
			"owner_revision":         ownerRev,
			"grant_id":               nil,
			"retry_epoch":            nil,
			"identity_source":        "receipt_json",
			"grant_epoch_alias":      "unobserved_on_first_edit_row",
		}
		claims = append(claims, rec)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	transfers := make([]map[string]any, 0, transferCount)
	if transferCount > 0 {
		trows, err := h.conn.QueryContext(h.carried, `SELECT call_id, grant_id, task_id, transfer_json FROM ordinary_retry_retained_grant_transfers WHERE session_id=? ORDER BY call_id`, h.epoch.SessionID)
		if err != nil {
			return nil, err
		}
		defer trows.Close()
		for trows.Next() {
			var id, grantID, taskID, transferRaw string
			if err := trows.Scan(&id, &grantID, &taskID, &transferRaw); err != nil {
				return nil, err
			}
			var ownerRev any = nil
			var retryEpoch any = nil
			var parsed map[string]any
			if json.Unmarshal([]byte(transferRaw), &parsed) == nil {
				if v, ok := parsed["owner_revision"].(float64); ok {
					ownerRev = int64(v)
				}
				if v, ok := parsed["retry_epoch"].(string); ok {
					retryEpoch = v
				} else if v, ok := parsed["episode_id"].(string); ok {
					// Observed alias: transfer JSON stores episode_id for epoch scope.
					retryEpoch = v
				}
			}
			transfers = append(transfers, map[string]any{
				"call_id":         id,
				"grant_id":        grantID,
				"task_id":         taskID,
				"owner_revision":  ownerRev,
				"retry_epoch":     retryEpoch,
				"identity_source": "transfer_row+json",
			})
		}
		if err := trows.Err(); err != nil {
			return nil, err
		}
	}
	// After transfers exist, bind claim grant/epoch from matching transfer rows
	// (observed), not from the fixture template.
	byCall := map[string]map[string]any{}
	for _, t := range transfers {
		if id, ok := t["call_id"].(string); ok {
			byCall[id] = t
		}
	}
	for i := range claims {
		id, _ := claims[i]["call_id"].(string)
		if t, ok := byCall[id]; ok {
			claims[i]["grant_id"] = t["grant_id"]
			claims[i]["retry_epoch"] = t["retry_epoch"]
			if claims[i]["task_id"] == "" || claims[i]["task_id"] == nil {
				claims[i]["task_id"] = t["task_id"]
			}
			if claims[i]["owner_revision"] == nil {
				claims[i]["owner_revision"] = t["owner_revision"]
			}
			claims[i]["grant_epoch_alias"] = "from_matching_transfer_row"
		}
	}
	spent := transferCount > 0
	if h.fixture.InitialSpent && transferCount == 0 {
		spent = true
	}
	return map[string]any{
		"grant_spent":       spent,
		"claim_count":       len(claims),
		"transfer_count":    len(transfers),
		"claims":            claims,
		"transfers":         transfers,
		"claim_call_ids":    callIDs,
		"transfer_call_ids": transferCallIDs(transfers),
		// Side-channel for auditors; comparator project_state ignores this key.
		"observed_identities": map[string]any{
			"claims":    claims,
			"transfers": transfers,
			"note":      "grant_id/task_id/owner_revision/retry_epoch read from durable rows/JSON; not fixture-filled",
		},
	}, nil
}

func transferCallIDs(transfers []map[string]any) []string {
	out := make([]string, 0, len(transfers))
	for _, t := range transfers {
		if id, ok := t["call_id"].(string); ok {
			out = append(out, id)
		}
	}
	return out
}

func (h *swarmWitnessR3Handle) reopen(ctx context.Context) error {
	// Cold handle reopen against the same sqlite file: close the DB connection
	// and reopen it. Keep the live session fence — a claimed retry intentionally
	// prevents Acquire from reclaiming, and the measured property is persistence
	// of claim/transfer rows across a connection cycle (no remint / no replay).
	sc := swarmWitnessR3Sidecar{
		Root: h.root, Path: h.path, Files: h.files, Workspace: h.workspace,
		Pre: h.pre, Post: h.post, Fixture: h.fixture,
	}
	raw, err := json.Marshal(sc)
	if err != nil {
		return err
	}
	if err := os.WriteFile(sidecarPath(h.dbPath), raw, 0o600); err != nil {
		return err
	}
	old := h.conn
	if err := old.Close(); err != nil {
		return err
	}
	h.conn = nil
	reopenCtx := context.Background()
	if ctx != nil {
		if deadline, ok := ctx.Deadline(); ok {
			var cancel context.CancelFunc
			reopenCtx, cancel = context.WithDeadline(context.Background(), deadline)
			defer cancel()
		}
	}
	conn, err := db.ConnectPath(reopenCtx, h.dbPath)
	if err != nil {
		return err
	}
	h.conn = conn
	h.admissions = NewAdmissionStore(conn)
	snapshot, present, err := h.admissions.LatestWithRevision(h.carried, "session")
	if err != nil {
		return err
	}
	if !present {
		return fmt.Errorf("admission missing after reopen")
	}
	h.snapshot = snapshot
	var hint runloop.DiagnosticDeliveredSourcePathHint
	err = db.RunSQLTx(h.carried, conn, func(tx *sql.Tx) error {
		var e error
		hint, e = ResolveOrdinaryRetryViewHintTx(h.carried, tx, h.epoch, h.root, h.path, h.files)
		return e
	})
	if err != nil {
		return err
	}
	h.hint = hint
	return nil
}

func seedSwarmWitnessR3(ctx context.Context, dbPath string, fixture probeCaseFixture) (*swarmWitnessR3Handle, error) {
	conn, err := db.ConnectPath(ctx, dbPath)
	if err != nil {
		return nil, err
	}
	owned, release, err := sessionfence.Acquire(ctx, conn, "session")
	if err != nil {
		_ = conn.Close()
		return nil, err
	}
	fail := func(e error) (*swarmWitnessR3Handle, error) {
		release()
		_ = conn.Close()
		return nil, e
	}
	_, err = db.New(conn).CreateSession(owned, db.CreateSessionParams{ID: "session", Title: "synthetic retained grant"})
	if err != nil {
		return fail(err)
	}
	messages := message.NewService(db.New(conn), conn)
	task, err := messages.Create(owned, "session", message.CreateMessageParams{Role: message.User, Parts: []message.ContentPart{message.TextContent{Text: "synthetic original task"}}})
	if err != nil {
		return fail(err)
	}
	ws := filepath.Join(filepath.Dir(dbPath), "workspace")
	if err := os.MkdirAll(ws, 0o755); err != nil {
		return fail(err)
	}
	root, err := filepath.EvalSymlinks(ws)
	if err != nil {
		return fail(err)
	}
	targetPath := filepath.Join(root, "answer.go")
	if err := os.WriteFile(targetPath, []byte("synthetic source"), 0o600); err != nil {
		return fail(err)
	}
	path := "answer.go"
	target := fmt.Sprintf("repair_target:%s", sha256Hex([]byte(path))[:16])
	reason := "authority_refreshed_for_bounded_progress"
	a := Admission{Observed: true, OwnerRunID: "session", OwnerTurn: 6, OwnerDecisionID: "decision", WorkConvergenceReadTaskID: task.ID, WorkConvergenceRequired: true, WorkConvergenceAction: "constrain_next_turn", WorkConvergenceOutcome: "pending", WorkConvergenceReason: "post_compaction_verification_failed", FrontierKind: "verification", FrontierSelectedOutcome: "degraded_continue", FrontierAdmissibleActionClasses: []string{"bounded_owner_evidence_read", "handoff_package"}, FrontierBlockedActionClasses: []string{"broad_discovery", "repeat_same_failed_action", "provider_narration_only"}, DiagnosticDecisionAction: "allow_mutation", DiagnosticDecisionReason: "typed_repairable_verifier_failure", DiagnosticVerificationBlocked: true, DiagnosticBroadDiscoveryBlocked: true, DiagnosticReadOnlyRoundConstrained: true, DiagnosticReadOnlyRoundCount: 5, DiagnosticReadOnlyRoundAppliedThreshold: 3, DiagnosticReadOnlyRoundDenyThreshold: 20, DiagnosticRepairAdmitted: true, DiagnosticRepairAuthorityOwnerRunID: "session", DiagnosticRepairAuthorityOwnerTurn: 6, DiagnosticRepairAuthorityOwnerDecisionID: "decision", DiagnosticRepairAuthorityTaskID: task.ID, DiagnosticRepairAuthorityFundingEvidenceID: "view", DiagnosticRepairAuthorityFingerprint: "fingerprint", DiagnosticRepairAuthorityBindingRevision: 1, DiagnosticRecoveryEpisodeTaskID: task.ID, DiagnosticRecoveryPredecessorVerifierID: "check-1", DiagnosticVerifierResultKind: "repairable_verifier_failure", DiagnosticVerifierResultEvidenceFingerprint: "failure", DiagnosticRecoveryEpisodeID: "check-1:repairable_verifier_failure:failure", DiagnosticRecoverySuccessorAction: "allow_mutation", WorkConvergenceLatestVerificationToolCallID: "check-1", WorkConvergenceLatestVerificationOutcome: "verification_failed", DiagnosticRecoveryObservedOwnerEvidenceID: "view", DiagnosticRecoveryApprovedRepairTargetIDs: []string{target}, DiagnosticDeliveredSourcePathHint: runloop.DiagnosticDeliveredSourcePathHint{TaskID: task.ID, CallID: "view", Path: path, TargetID: target, ResultDigest: "pending", WorkspaceRootDigest: "sha256:" + sha256Hex([]byte(root)), ResolvedPathDigest: "sha256:" + sha256Hex([]byte(targetPath))}, DiagnosticBoundedReadSetComplete: true, DiagnosticBoundedReadActions: []runloop.DiagnosticBoundedReadAction{{ToolName: "view", Path: path, TargetKind: runloop.DiagnosticTargetKindFile}}, DiagnosticPostVerifierReadWindow: runloop.DiagnosticPostVerifierReadWindow{TaskID: task.ID, EpisodeID: "check-1:repairable_verifier_failure:failure", VerifierID: "check-1", BaseCount: 3, Limit: 3}, DiagnosticReopenReason: reason}
	a.IngressLineageToolCallIDs = []string{"check-1", "view"}
	a.WorkConvergenceObservationIdentities = []string{"check-1", "view"}
	a.DiagnosticRepairAuthorityGrantID = sha256Hex([]byte("session\n6\nview\nfingerprint\n" + reason))
	a.DiagnosticReadOnlyRoundCount = 4
	a.IngressLineageToken = SignAdmissionIngressLineage(a)
	admissions := NewAdmissionStore(conn)
	if err := admissions.Save(owned, "session", a); err != nil {
		return fail(err)
	}
	before, present, err := admissions.LatestWithRevision(owned, "session")
	if err != nil || !present {
		if err == nil {
			err = fmt.Errorf("admission missing")
		}
		return fail(err)
	}
	call := message.ToolCall{ID: "view", Name: "view", Input: `{"file_path":"answer.go"}`}
	receipt, err := PostVerifierReadAdmission(before, "admitted-turn", "envelope", call.ID, call.Name, call.Input)
	if err != nil {
		return fail(err)
	}
	outcome := map[string]string{"view_source_target_sha256": sha256Hex([]byte(targetPath))}
	encoded, err := CompletePostVerifierRead(receipt, call.Name, "synthetic source", outcome)
	if err != nil {
		return fail(err)
	}
	outcome[bmoitools.PostVerifierReadReceiptMetadataKey] = encoded
	metadata, err := json.Marshal(outcome)
	if err != nil {
		return fail(err)
	}
	result := message.ToolResult{ToolCallID: "view", Name: "view", Content: "synthetic source", ExecutionState: "executed", Metadata: string(metadata)}
	if _, err = messages.Create(owned, "session", message.CreateMessageParams{Role: message.Assistant, Parts: []message.ContentPart{call}}); err != nil {
		return fail(err)
	}
	resultMessage, err := messages.Create(owned, "session", message.CreateMessageParams{Role: message.Tool, Parts: []message.ContentPart{result}})
	if err != nil {
		return fail(err)
	}
	converted, err := bridge.MessagesToBMOi([]message.Message{{Role: message.Assistant, Parts: []message.ContentPart{call}}, {Role: message.Tool, Parts: []message.ContentPart{result}}}, "session")
	if err != nil {
		return fail(err)
	}
	for _, m := range converted {
		for _, p := range m.Content.Parts {
			if p.Type == "tool_result" {
				a.DiagnosticDeliveredSourcePathHint.ResultDigest = ordinaryrepair.DeliveredSourceResultDigest("view", p)
			}
		}
	}
	for _, kind := range []string{"call", "read"} {
		id := ingresslineage.ObservationIdentity(kind, "id:view")
		a.WorkConvergenceObservationIdentities = append(a.WorkConvergenceObservationIdentities, id)
		a.IngressLineageToolCallIDs = append(a.IngressLineageToolCallIDs, id)
	}
	runs, intents := runevents.NewSQLiteStore(conn), runevents.NewRetryIntentStore(conn)
	if err := runs.UpsertRun(owned, runevents.AgentRunRecord{RunID: "root", SessionID: "session", MessageID: task.ID, Status: runevents.RunStatusFailed, CompletedAtMs: 100}); err != nil {
		return fail(err)
	}
	pre, post, workspace, verifier, command, failure := strings.Repeat("a", 64), strings.Repeat("b", 64), strings.Repeat("c", 64), strings.Repeat("d", 64), strings.Repeat("e", 64), strings.Repeat("f", 64)
	identity := sha256Hex([]byte(root + "\x00rev\x00" + verifier + "\x00" + command))
	files := map[string]string{path: "observed:100644:" + post}
	meta := map[string]string{"execution_authority": "bmo", "edit_write_state": "entered", "edit_source_base_sha256": pre, "edit_source_after_sha256": post, "edit_after_effect_state_sha256": strings.Repeat("1", 64)}
	store := runtimeevidence.NewSQLiteStore(conn)
	appendRow := func(kind, stage string, payload any) error {
		raw, e := json.Marshal(payload)
		if e != nil {
			return e
		}
		_, e = store.AppendNext(owned, runtimeevidence.ObservationRecord{RunID: "root", TurnID: task.ID, Kind: kind, StageOrName: stage, Source: runtimeevidence.SourceRuntimeProducer, PayloadJSON: string(raw)})
		return e
	}
	if err := appendRow(runtimeevidence.KindTool, "edit", map[string]any{"tool_name": "edit", "tool_call_id": "edit-1", "success": true, "metadata": meta}); err != nil {
		return fail(err)
	}
	if err := appendRow(runtimeevidence.KindMutation, "file_write", map[string]any{"tool_name": "edit", "tool_call_id": "edit-1", "file_path": targetPath, "metadata": meta}); err != nil {
		return fail(err)
	}
	if err := appendRow("ordinary_verifier_observation", "ordinary_verifier_failure", map[string]any{"call_id": "check-1", "command_sha256": command, "verifier_identity": identity, "workspace_identity": workspace, "source_sha256": files, "predicate": "go_test_failure", "failure_sha256": failure, "failure_identity_version": 1, "disposition": "observed_failure"}); err != nil {
		return fail(err)
	}
	if err := appendRow("ordinary_verifier_execution", "shell_verifier", ordinaryEpochVerifierExecution{Version: 1, CallID: "check-1", CommandSHA256: command, VerifierIdentity: identity, CheckoutRoot: root, CheckoutRevision: "rev", VerifierSHA256: verifier, WorkspaceIdentity: workspace, SourceSHA256: files, ExitCode: 1}); err != nil {
		return fail(err)
	}
	if err := appendRow(runtimeevidence.KindTool, "bash", map[string]any{"tool_name": "bash", "tool_call_id": "check-1", "success": true, "metadata": map[string]string{"execution_authority": "bmo", "tool_execution_state": "executed", "tool_exit_code": "1", "tool_result_success": "true", "tool_working_directory": root}}); err != nil {
		return fail(err)
	}
	if err := appendRow(runtimeevidence.KindTool, "view", map[string]any{"tool_name": "view", "tool_call_id": "view", "success": true, "metadata": map[string]string{"execution_authority": "bmo", "tool_execution_state": "executed", "tool_result_success": "true", "view_source_target_sha256": sha256Hex([]byte(targetPath))}}); err != nil {
		return fail(err)
	}
	a.DiagnosticReadOnlyRoundCount = 5
	a.WorkConvergenceReadOnlyToolCallCount++
	a.WorkConvergenceObservedToolCallCount++
	a.WorkConvergenceLatestToolCommand = "diagnostic:view"
	a.WorkConvergenceDeclaredVerificationExecuted = true
	a.IngressLineageToken = SignAdmissionIngressLineage(a)
	seeded, err := json.Marshal(a)
	if err != nil {
		return fail(err)
	}
	seededDigest := admissionDigest(seeded)
	_, err = conn.ExecContext(owned, `UPDATE session_compaction_admissions SET admission_json=?, admission_digest=?, origin_attestation=?, owner_revision=owner_revision+1 WHERE session_id=?`, string(seeded), seededDigest, lifecycleprovenance.AttestDigest(admissionAttestationScope+seededDigest), "session")
	if err != nil {
		return fail(err)
	}
	snapshot, present, err := admissions.LatestWithRevision(owned, "session")
	if err != nil || !present {
		if err == nil {
			err = fmt.Errorf("snapshot missing")
		}
		return fail(err)
	}
	if !OrdinaryRetryRetainedGrantShapeEligible(snapshot, "session", task.ID, root, taskcheckout.ContractPin{}) {
		return fail(fmt.Errorf("shape not eligible after seed"))
	}
	records, err := store.ListRun(owned, "root", 4001)
	if err != nil {
		return fail(err)
	}
	rawRecords, err := json.Marshal(records)
	if err != nil {
		return fail(err)
	}
	frontier := ordinaryEpochSourceFrontier{RunID: "root", EvidenceCeiling: records[len(records)-1].Seq, MessageCeiling: resultMessage.Seq, ObservationsSHA: sha256Hex(rawRecords), SourceStatus: "failed", HasEdits: true, ShellVerifierCommandSHA: command, ShellVerifierIdentity: identity}
	rawFrontier, err := json.Marshal(frontier)
	if err != nil {
		return fail(err)
	}
	frontier.FrontierSHA256 = sha256Hex(append([]byte("bmo/ordinary-settled-effect-frontier/v1\x00"), rawFrontier...))
	bind := RecoveryRetryTranscriptBinding{IntentID: "intent", SourceRunID: "root", OriginRunID: "root", OwnerSessionID: "session", TaskID: task.ID, Route: "v2", ExpectedOwnerRevision: snapshot.Revision, ExpectedAdmissionDigest: snapshot.Digest, OriginalAppRequestSHA256: sha256Hex([]byte("original")), GeneratedPromptSHA256: sha256Hex([]byte("generated")), OrdinaryFailure: &OrdinaryFailedSource{FrontierSHA256: frontier.FrontierSHA256, SourceStatus: "failed"}}
	tx, err := conn.BeginTx(owned, nil)
	if err != nil {
		return fail(err)
	}
	att, err := RecoveryRetryTranscriptAttestationTx(owned, tx, bind)
	if err != nil {
		_ = tx.Rollback()
		return fail(err)
	}
	if err := tx.Commit(); err != nil {
		return fail(err)
	}
	payload, err := json.Marshal(ordinaryEpochSourcePayload{Version: 1, Frontier: frontier, OwnerRevision: snapshot.Revision, OwnerDigest: snapshot.Digest, BudgetLimit: 10, BudgetUsed: 4, OriginalPromptSHA256: bind.OriginalAppRequestSHA256, GeneratedPromptSHA256: bind.GeneratedPromptSHA256, TranscriptAttestation: att})
	if err != nil {
		return fail(err)
	}
	intent := runevents.RetryIntent{ID: "intent", SourceRunID: "root", OriginRunID: "root", OwnerSessionID: "session", TaskID: task.ID, Ordinal: 1, PayloadJSON: string(payload)}
	if err := intents.CreateGuardedFailedRoot(owned, intent, func(context.Context, *sql.Tx) error { return nil }); err != nil {
		return fail(err)
	}
	var epoch OrdinaryRetryEpoch
	err = db.RunSQLTx(owned, conn, func(tx *sql.Tx) error {
		if e := intents.ClaimTx(owned, tx, intent.ID, "retry"); e != nil {
			return e
		}
		var e error
		epoch, e = BindOrdinaryRetryEpochTx(owned, tx, OrdinaryRetryEpoch{SessionID: "session", RootRunID: "root", TaskID: task.ID, SourceRunID: "root", RetryRunID: "retry", IntentID: intent.ID, OwnerRevision: snapshot.Revision, OwnerDigest: snapshot.Digest})
		return e
	})
	if err != nil {
		return fail(err)
	}
	carried := WithOrdinaryRetryEpoch(owned, epoch)
	binding := taskcheckout.Binding{CheckoutRoot: root, Revision: "rev", VerifierPath: "answer_test.go", VerifierSHA256: verifier, VerifierCommandSHA256: command}
	err = db.RunSQLTx(carried, conn, func(tx *sql.Tx) error {
		_, e := ReadOrdinaryRetryRetainedGrantOwnerTx(carried, tx, epoch, root, taskcheckout.ContractPin{}, binding)
		return e
	})
	if err != nil {
		return fail(err)
	}
	retryView := message.ToolCall{ID: "retry-view", Name: "view", Input: `{"file_path":"answer.go"}`}
	if _, err = messages.Create(carried, "session", message.CreateMessageParams{Role: message.Assistant, Parts: []message.ContentPart{retryView}}); err != nil {
		return fail(err)
	}
	var viewClaim OrdinaryRetryBoundedViewClaim
	var readOffer PostVerifierReadReceipt
	err = db.RunSQLTx(carried, conn, func(tx *sql.Tx) error {
		var e error
		viewClaim, readOffer, e = admissions.ClaimOrdinaryRetryBoundedViewWithPostVerifierReceiptTx(carried, tx, epoch, taskcheckout.ContractPin{}, binding, OrdinaryRetryBoundedViewRequest{CallID: retryView.ID, ArgumentsJSON: retryView.Input, CheckoutRoot: root}, "synthetic-admission", "synthetic-envelope")
		return e
	})
	if err != nil {
		return fail(err)
	}
	_ = viewClaim
	retryOutcome := map[string]string{"view_source_sha256": post, "view_source_target_sha256": sha256Hex([]byte(targetPath)), "view_read_offset": "0", "view_read_lines": "1", "view_read_char_offset": "0", "view_read_line_truncated": "false", "view_result_sha256": sha256Hex([]byte("synthetic source"))}
	readOrigin, err := CompletePostVerifierReadResult(readOffer, "view", "synthetic source", retryOutcome, false)
	if err != nil {
		return fail(err)
	}
	retryOutcome[bmoitools.PostVerifierReadReceiptMetadataKey] = readOrigin
	retryMetadata, err := json.Marshal(retryOutcome)
	if err != nil {
		return fail(err)
	}
	retryResult := message.ToolResult{ToolCallID: retryView.ID, Name: "view", Content: "synthetic source", Metadata: string(retryMetadata), ExecutionState: "executed"}
	if err := validatePostVerifierReadResult(snapshot, retryView, retryResult); err != nil {
		return fail(err)
	}
	if _, err = messages.Create(carried, "session", message.CreateMessageParams{Role: message.Tool, Parts: []message.ContentPart{retryResult}}); err != nil {
		return fail(err)
	}
	appendRetry := func(kind, stage string, payload any) error {
		raw, e := json.Marshal(payload)
		if e != nil {
			return e
		}
		_, e = store.AppendNext(carried, runtimeevidence.ObservationRecord{RunID: "retry", TurnID: task.ID, Kind: kind, StageOrName: stage, Source: runtimeevidence.SourceRuntimeProducer, PayloadJSON: string(raw)})
		return e
	}
	retryReceipt := ordinaryrepair.RetryViewReceipt{Version: 1, EpochDigest: OrdinaryRetryEpochDigest(epoch), RetryRunID: "retry", TaskID: task.ID, CallID: retryView.ID, CheckoutRoot: root, Path: path, WorkspaceRootSHA256: sha256Hex([]byte(root)), ResolvedPathSHA256: sha256Hex([]byte(targetPath)), TargetSHA256: sha256Hex([]byte(targetPath)), SourceSHA256: post, ResultSHA256: sha256Hex([]byte(retryResult.Content))}
	if err := appendRetry("ordinary_retry_view_read", "view", retryReceipt); err != nil {
		return fail(err)
	}
	if err := appendRetry(runtimeevidence.KindTool, "view", map[string]any{"tool_name": "view", "tool_call_id": retryView.ID, "success": true, "metadata": map[string]string{"tool_execution_state": "executed", "execution_authority": "bmo"}}); err != nil {
		return fail(err)
	}
	err = db.RunSQLTx(carried, conn, func(tx *sql.Tx) error {
		return admissions.SettleOrdinaryRetryBoundedViewTx(carried, tx, epoch, retryView.ID)
	})
	if err != nil {
		return fail(err)
	}
	candidate := snapshot.Admission.clone()
	candidate.DiagnosticReadOnlyRoundCount++
	candidate.WorkConvergenceReadOnlyToolCallCount++
	candidate.WorkConvergenceObservedToolCallCount++
	for _, kind := range []string{"call", "read"} {
		id := ingresslineage.ObservationIdentity(kind, "id:"+retryView.ID)
		candidate.WorkConvergenceObservationIdentities = append(candidate.WorkConvergenceObservationIdentities, id)
		candidate.IngressLineageToolCallIDs = append(candidate.IngressLineageToolCallIDs, id)
	}
	candidate.WorkConvergenceAccumulatedObservationIdentities = slices.Clone(candidate.WorkConvergenceObservationIdentities)
	candidate.WorkConvergenceReadCoverage = []runloop.SemanticReadCoverage{{TargetSHA256: sha256Hex([]byte(targetPath)), SourceSHA256: post, StartLine: 0, EndLine: 1}}
	candidate.WorkConvergenceReadCursor = strings.Repeat("c", 64)
	candidate.AfterEnvelopeFingerprint = strings.Repeat("b", 64)
	candidate.IngressLineageToken = SignAdmissionIngressLineage(candidate)
	err = db.RunSQLTx(carried, conn, func(tx *sql.Tx) error {
		_, e := PreviewOrdinaryRetainedReadTransitionTx(carried, tx, epoch, root, taskcheckout.ContractPin{}, binding, candidate)
		return e
	})
	if err != nil {
		return fail(err)
	}
	var hint runloop.DiagnosticDeliveredSourcePathHint
	err = db.RunSQLTx(carried, conn, func(tx *sql.Tx) error {
		var e error
		hint, e = ResolveOrdinaryRetryViewHintTx(carried, tx, epoch, root, path, files)
		return e
	})
	if err != nil {
		return fail(err)
	}
	h := &swarmWitnessR3Handle{
		dbPath: dbPath, conn: conn, release: release, owned: owned, carried: carried,
		admissions: admissions, epoch: epoch, snapshot: snapshot, binding: binding,
		root: root, path: path, files: files, workspace: workspace, pre: pre, post: post,
		hint: hint, fixture: fixture, taskID: task.ID,
	}
	sc := swarmWitnessR3Sidecar{
		Root: root, Path: path, Files: files, Workspace: workspace, Pre: pre, Post: post, Fixture: fixture,
	}
	raw, err := json.Marshal(sc)
	if err != nil {
		return fail(err)
	}
	if err := os.WriteFile(sidecarPath(dbPath), raw, 0o600); err != nil {
		return fail(err)
	}
	return h, nil
}

func unsupportedObs(cse probeCase, act probeCaseAction, reason string) stepObservation {
	return stepObservation{
		ProtocolID: "r3-ledger-claim-v1", CaseID: cse.CaseID, Step: act.Step, Op: act.Op,
		AdapterID: "bmo_l1_first_edit", ExecutionStatus: "missing", Disposition: "unsupported",
		Inputs: actionInputs(act), NativeResult: map[string]any{"reason": reason}, Notes: reason,
	}
}

func failedObs(cse probeCase, act probeCaseAction, err error) stepObservation {
	return stepObservation{
		ProtocolID: "r3-ledger-claim-v1", CaseID: cse.CaseID, Step: act.Step, Op: act.Op,
		AdapterID: "bmo_l1_first_edit", ExecutionStatus: "failed", Disposition: "error",
		Inputs: actionInputs(act), NativeResult: map[string]any{"error": err.Error()}, Notes: err.Error(),
	}
}
