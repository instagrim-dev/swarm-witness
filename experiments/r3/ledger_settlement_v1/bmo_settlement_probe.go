//go:build swarm_witness_r3

package sessioncompaction

// Settlement continuation for protocol r3-ledger-settlement-v1.
//
// Injected beside the claim bridge into a disposable BMO tree. After a
// committed ClaimOrdinaryRetainedGrantFirstEditTx, this file calls the
// production settlement transactions:
//
//   - SettleOrdinaryRetryFirstEditTx
//   - SettleOrdinaryRetryFirstEditNoEffectTx
//
// The native tool, mutation, artifact, and no-effect rows are the records
// those transactions require. They are fixture-authored inputs to the
// production settler, not a live model edit.

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"

	"github.com/instagrim-dev/bmo/internal/db"
	"github.com/instagrim-dev/bmo/internal/lifecycleprovenance"
	"github.com/instagrim-dev/bmo/internal/message"
	"github.com/instagrim-dev/bmo/internal/runevents"
	"github.com/instagrim-dev/bmo/internal/runtimeevidence"
)

const swarmWitnessR3EditInput = `{"file_path":"answer.go","new_string":"new","old_string":"old"}`

func init() {
	prior := swarmWitnessR3Apply
	swarmWitnessR3Apply = func(ctx context.Context, store any, cse probeCase, act probeCaseAction) (stepObservation, error) {
		if act.Op == "settle_applied" || act.Op == "settle_no_effect" {
			return settleSwarmWitnessR3(ctx, store, cse, act)
		}
		row, err := prior(ctx, store, cse, act)
		row.ProtocolID = swarmWitnessR3ProtocolID
		if err == nil && act.Op == "inspect" {
			if h, ok := store.(*swarmWitnessR3Handle); ok && row.State != nil {
				settlement, sErr := readSwarmWitnessSettlement(h)
				if sErr != nil {
					failed := failedObs(cse, act, sErr)
					failed.ProtocolID = swarmWitnessR3ProtocolID
					return failed, sErr
				}
				row.State["settlement"] = settlement
			}
		}
		return row, err
	}
}

func settleSwarmWitnessR3(ctx context.Context, store any, cse probeCase, act probeCaseAction) (stepObservation, error) {
	h, ok := store.(*swarmWitnessR3Handle)
	if !ok || h == nil {
		row := unsupportedObs(cse, act, "bad_handle")
		row.ProtocolID = swarmWitnessR3ProtocolID
		return row, fmt.Errorf("bad handle")
	}
	var settleErr error
	evidence := act.Evidence
	if evidence == "" {
		evidence = "bound"
	}
	switch act.Op {
	case "settle_applied":
		settleErr = h.recordApplied(ctx, act.CallID, evidence)
	case "settle_no_effect":
		settleErr = h.recordNoEffect(ctx, act.CallID, evidence)
	default:
		settleErr = fmt.Errorf("unknown settlement op %q", act.Op)
	}
	state, err := h.projectState()
	if err != nil {
		failed := failedObs(cse, act, err)
		failed.ProtocolID = swarmWitnessR3ProtocolID
		return failed, err
	}
	settlement, sErr := readSwarmWitnessSettlement(h)
	if sErr != nil {
		failed := failedObs(cse, act, sErr)
		failed.ProtocolID = swarmWitnessR3ProtocolID
		return failed, sErr
	}
	state["settlement"] = settlement
	disposition := "committed"
	reason := "ok"
	if settleErr != nil {
		disposition = "refused"
		reason = settleErr.Error()
	}
	return stepObservation{
		ProtocolID:      swarmWitnessR3ProtocolID,
		CaseID:          cse.CaseID,
		Step:            act.Step,
		Op:              act.Op,
		AdapterID:       "bmo_l1_first_edit",
		ExecutionStatus: "completed",
		Disposition:     disposition,
		Inputs:          map[string]any{"call_id": act.CallID, "outcome": act.Outcome, "evidence": evidence},
		NativeResult: map[string]any{
			"native_bmo": true,
			"native_ok":  settleErr == nil,
			"reason":     reason,
			"call_id":    act.CallID,
		},
		State: state,
		Notes: reason,
	}, nil
}

func (h *swarmWitnessR3Handle) loadClaim() (OrdinaryRetryFirstEditReceipt, error) {
	var receipt OrdinaryRetryFirstEditReceipt
	err := db.RunSQLTx(h.carried, h.conn, func(tx *sql.Tx) error {
		loaded, _, found, err := loadOrdinaryRetryFirstEditClaimTx(h.carried, tx, h.epoch)
		if err != nil {
			return err
		}
		if !found {
			return fmt.Errorf("no committed claim")
		}
		receipt = loaded
		return nil
	})
	return receipt, err
}

func (h *swarmWitnessR3Handle) recordApplied(ctx context.Context, callID, evidence string) error {
	claim, err := h.loadClaim()
	if err != nil {
		return err
	}
	if claim.CallID != callID {
		return fmt.Errorf("call_id mismatch")
	}
	if evidence == "missing" {
		return db.RunSQLTx(h.carried, h.conn, func(tx *sql.Tx) error {
			return SettleOrdinaryRetryFirstEditTx(h.carried, tx, h.epoch, claim.CallID)
		})
	}
	if evidence == "unrelated" {
		return h.settleAppliedAfterUnrelated(claim)
	}
	runs := runevents.NewSQLiteStore(h.conn)
	if err := runs.UpsertRun(h.owned, runevents.AgentRunRecord{RunID: "retry", SessionID: "session", Status: runevents.RunStatusStarted}); err != nil {
		return err
	}
	targetPath := filepath.Join(h.root, h.path)
	editMeta := map[string]string{
		"execution_authority":     "bmo",
		"tool_execution_state":    "executed",
		"edit_write_state":        "entered",
		"edit_source_base_sha256": claim.TargetBeforeSHA256,
		"edit_source_after_sha256": claim.TargetAfterSHA256,
	}
	store := runtimeevidence.NewSQLiteStore(h.conn)
	if err := appendSwarmWitnessRetry(h, store, runtimeevidence.KindTool, "edit", map[string]any{
		"tool_name": "edit", "tool_call_id": claim.CallID, "success": true, "metadata": editMeta,
	}); err != nil {
		return err
	}
	eventMeta, err := json.Marshal(map[string]string{"file_path": targetPath})
	if err != nil {
		return err
	}
	event := runevents.AgentRunEventRecord{RunID: "retry", Seq: 77, OccurredAtMs: 123, Kind: "artifact", StageOrName: "file_write", MetadataJSON: string(eventMeta)}
	if err := runs.AppendEvent(h.owned, event); err != nil {
		return err
	}
	if _, err := store.AppendNext(h.carried, runtimeevidence.FromAgentRunEvent(event)); err != nil {
		return err
	}
	mutationCall := claim.CallID
	artifactCall := claim.CallID
	if evidence == "wrong_call" {
		mutationCall = "call-foreign"
		artifactCall = "call-foreign"
	}
	appendMutation := func() error {
		return appendSwarmWitnessRetry(h, store, runtimeevidence.KindMutation, "file_write", map[string]any{
			"tool_name": "edit", "tool_call_id": mutationCall, "file_path": targetPath, "metadata": editMeta,
		})
	}
	appendArtifact := func() error {
		rawArtifact, err := json.Marshal(map[string]any{
			"tool_name": "edit", "tool_call_id": artifactCall, "file_path": targetPath,
			"artifact": map[string]string{"file_path": targetPath},
		})
		if err != nil {
			return err
		}
		_, err = store.AppendNext(h.carried, runtimeevidence.ObservationRecord{
			RunID: "retry", Kind: runtimeevidence.KindArtifact, StageOrName: "file_write",
			Source: runtimeevidence.SourceRuntimeProducer, SourceSeq: 77, PayloadJSON: string(rawArtifact),
		})
		return err
	}
	switch evidence {
	case "bound":
		if err := appendMutation(); err != nil {
			return err
		}
		if err := appendArtifact(); err != nil {
			return err
		}
	case "missing_mutation":
		if err := appendArtifact(); err != nil {
			return err
		}
	case "swapped":
		if err := appendArtifact(); err != nil {
			return err
		}
		if err := appendMutation(); err != nil {
			return err
		}
	case "wrong_call":
		if err := appendMutation(); err != nil {
			return err
		}
		if err := appendArtifact(); err != nil {
			return err
		}
	default:
		return fmt.Errorf("unknown applied evidence %q", evidence)
	}
	return db.RunSQLTx(h.carried, h.conn, func(tx *sql.Tx) error {
		return SettleOrdinaryRetryFirstEditTx(h.carried, tx, h.epoch, claim.CallID)
	})
}

func (h *swarmWitnessR3Handle) settleAppliedAfterUnrelated(claim OrdinaryRetryFirstEditReceipt) error {
	runs := runevents.NewSQLiteStore(h.conn)
	if err := runs.UpsertRun(h.owned, runevents.AgentRunRecord{RunID: "retry", SessionID: "session", Status: runevents.RunStatusStarted}); err != nil {
		return err
	}
	store := runtimeevidence.NewSQLiteStore(h.conn)
	if err := appendSwarmWitnessRetry(h, store, runtimeevidence.KindTool, "bash", map[string]any{
		"tool_name": "bash", "tool_call_id": "call-unrelated", "success": true,
		"metadata": map[string]string{"execution_authority": "bmo", "tool_execution_state": "executed"},
	}); err != nil {
		return err
	}
	return db.RunSQLTx(h.carried, h.conn, func(tx *sql.Tx) error {
		return SettleOrdinaryRetryFirstEditTx(h.carried, tx, h.epoch, claim.CallID)
	})
}

func (h *swarmWitnessR3Handle) appendContradictingWrite(callID string) error {
	runs := runevents.NewSQLiteStore(h.conn)
	if err := runs.UpsertRun(h.owned, runevents.AgentRunRecord{RunID: "retry", SessionID: "session", Status: runevents.RunStatusStarted}); err != nil {
		return err
	}
	store := runtimeevidence.NewSQLiteStore(h.conn)
	return appendSwarmWitnessRetry(h, store, runtimeevidence.KindMutation, "file_write", map[string]any{
		"tool_name": "edit", "tool_call_id": callID, "file_path": filepath.Join(h.root, h.path),
		"metadata": map[string]string{"execution_authority": "bmo", "tool_execution_state": "executed", "edit_write_state": "entered"},
	})
}

func (h *swarmWitnessR3Handle) recordNoEffect(ctx context.Context, callID, evidence string) error {
	_ = ctx
	if evidence == "write_present" {
		if err := h.appendContradictingWrite(callID); err != nil {
			return err
		}
	}
	if evidence == "missing" || evidence == "unrelated" {
		claim, err := h.loadClaim()
		if err != nil {
			return err
		}
		if claim.CallID != callID {
			return fmt.Errorf("call_id mismatch")
		}
		if evidence == "unrelated" {
			runs := runevents.NewSQLiteStore(h.conn)
			if err := runs.UpsertRun(h.owned, runevents.AgentRunRecord{RunID: "retry", SessionID: "session", Status: runevents.RunStatusStarted}); err != nil {
				return err
			}
			store := runtimeevidence.NewSQLiteStore(h.conn)
			if err := appendSwarmWitnessRetry(h, store, runtimeevidence.KindTool, "bash", map[string]any{
				"tool_name": "bash", "tool_call_id": "call-unrelated", "success": true,
				"metadata": map[string]string{"execution_authority": "bmo", "tool_execution_state": "executed"},
			}); err != nil {
				return err
			}
		}
		noEffect := OrdinaryRetryNoEffectReceipt{
			EpochDigest: OrdinaryRetryEpochDigest(h.epoch), RetryRunID: h.epoch.RetryRunID, TaskID: h.epoch.TaskID,
			CallID: claim.CallID, CheckoutRoot: h.root, WorkspaceSHA256: h.workspace, SourceSHA256: h.files,
		}
		digest, err := OrdinaryRetryNoEffectDigest(noEffect)
		if err != nil {
			return err
		}
		noEffect.Attestation = lifecycleprovenance.AttestDigest("ordinary-retry-no-effect/v1:" + digest)
		return db.RunSQLTx(h.carried, h.conn, func(tx *sql.Tx) error {
			return SettleOrdinaryRetryFirstEditNoEffectTx(h.carried, tx, h.epoch, noEffect)
		})
	}
	claim, err := h.loadClaim()
	if err != nil {
		return err
	}
	if claim.CallID != callID {
		return fmt.Errorf("call_id mismatch")
	}
	runs := runevents.NewSQLiteStore(h.conn)
	if err := runs.UpsertRun(h.owned, runevents.AgentRunRecord{RunID: "retry", SessionID: "session", Status: runevents.RunStatusStarted}); err != nil {
		return err
	}
	failed := message.ToolResult{ToolCallID: claim.CallID, Name: "edit", IsError: true, ExecutionState: "executed", Content: "synthetic pre-write rejection"}
	resultDigest := sha256Hex([]byte(failed.Content))
	proposalMeta, err := json.Marshal(map[string]string{"tool_call_id": claim.CallID, "ordinary_retry_edit_input_sha256": claim.InputSHA256})
	if err != nil {
		return err
	}
	proposal := runevents.AgentRunEventRecord{RunID: "retry", Seq: 76, OccurredAtMs: 121, Kind: "transcript", StageOrName: runevents.TranscriptStageToolCallProposed, Message: "edit", MetadataJSON: string(proposalMeta)}
	if err := runs.AppendEvent(h.owned, proposal); err != nil {
		return err
	}
	store := runtimeevidence.NewSQLiteStore(h.conn)
	if _, err := store.AppendNext(h.carried, runtimeevidence.FromAgentRunEvent(proposal)); err != nil {
		return err
	}
	if err := appendSwarmWitnessRetry(h, store, runtimeevidence.KindTool, "edit", map[string]any{
		"tool_name": "edit", "tool_call_id": claim.CallID, "success": false,
		"metadata": map[string]string{
			"execution_authority": "bmo", "tool_execution_state": "executed", "edit_write_state": "not_entered",
			"edit_source_base_sha256": claim.TargetBeforeSHA256, "ordinary_retry_result_sha256": resultDigest,
		},
	}); err != nil {
		return err
	}
	terminalMeta, err := json.Marshal(map[string]string{"tool_call_id": claim.CallID, "tool_result_success": "false", "ordinary_retry_result_sha256": resultDigest})
	if err != nil {
		return err
	}
	terminal := runevents.AgentRunEventRecord{RunID: "retry", Seq: 77, OccurredAtMs: 122, Kind: "transcript", StageOrName: runevents.TranscriptStageToolResult, MetadataJSON: string(terminalMeta)}
	if err := runs.AppendEvent(h.owned, terminal); err != nil {
		return err
	}
	if _, err := store.AppendNext(h.carried, runtimeevidence.FromAgentRunEvent(terminal)); err != nil {
		return err
	}
	messages := message.NewService(db.New(h.conn), h.conn)
	input := swarmWitnessR3EditInput
	if _, err := messages.Create(h.carried, "session", message.CreateMessageParams{Role: message.Assistant, Parts: []message.ContentPart{message.ToolCall{ID: claim.CallID, Name: "edit", Input: input}}}); err != nil {
		return err
	}
	if _, err := messages.Create(h.carried, "session", message.CreateMessageParams{Role: message.Tool, Parts: []message.ContentPart{failed}}); err != nil {
		return err
	}
	noEffect := OrdinaryRetryNoEffectReceipt{
		EpochDigest: OrdinaryRetryEpochDigest(h.epoch), RetryRunID: h.epoch.RetryRunID, TaskID: h.epoch.TaskID,
		CallID: claim.CallID, CheckoutRoot: h.root, WorkspaceSHA256: h.workspace, SourceSHA256: h.files,
	}
	digest, err := OrdinaryRetryNoEffectDigest(noEffect)
	if err != nil {
		return err
	}
	noEffect.Attestation = lifecycleprovenance.AttestDigest("ordinary-retry-no-effect/v1:" + digest)
	return db.RunSQLTx(h.carried, h.conn, func(tx *sql.Tx) error {
		return SettleOrdinaryRetryFirstEditNoEffectTx(h.carried, tx, h.epoch, noEffect)
	})
}

func appendSwarmWitnessRetry(h *swarmWitnessR3Handle, store *runtimeevidence.SQLiteStore, kind, stage string, payload any) error {
	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	_, err = store.AppendNext(h.carried, runtimeevidence.ObservationRecord{
		RunID: "retry", TurnID: h.taskID, Kind: kind, StageOrName: stage,
		Source: runtimeevidence.SourceRuntimeProducer, PayloadJSON: string(raw),
	})
	return err
}

func readSwarmWitnessSettlement(h *swarmWitnessR3Handle) (map[string]any, error) {
	var disposition, callID, toolID, mutationID, artifactID, sourceSHA string
	err := h.conn.QueryRowContext(h.carried, `SELECT disposition,call_id,tool_observation_id,mutation_observation_id,artifact_observation_id,source_receipt_sha256 FROM ordinary_retry_first_edit_settlements WHERE session_id=? AND generation=?`, h.epoch.SessionID, h.epoch.Generation).Scan(&disposition, &callID, &toolID, &mutationID, &artifactID, &sourceSHA)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"disposition":           disposition,
		"call_id":               callID,
		"tool_bound":            toolID != "",
		"mutation_bound":        mutationID != "",
		"artifact_bound":        artifactID != "",
		"source_receipt_bound":  sourceSHA != "",
	}, nil
}
