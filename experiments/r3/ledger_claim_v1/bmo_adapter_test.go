//go:build swarm_witness_r3

// Test-only bridge for protocol r3-ledger-claim-v1.
// Stored in swarm-witness and copied into a disposable BMO tree at the pinned
// revision (internal/sessioncompaction). Invokes ClaimOrdinaryRetainedGrantFirstEditTx;
// does not use ShapeEligible as the admission result. Unexpected second claims
// are serialized as counterexamples (no fatal expectation on refuse).
//
// SWARM_WITNESS_R3_CASES = absolute path to case-input JSON
// SWARM_WITNESS_R3_OUT   = absolute path for NDJSON observations
//
//	go test -tags=swarm_witness_r3 ./internal/sessioncompaction/ \
//	  -run '^TestSwarmWitnessR3Probe$' -count=1

package sessioncompaction

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"
)

type probeCaseAction struct {
	Step                   int    `json:"step"`
	Op                     string `json:"op"`
	CallID                 string `json:"call_id"`
	TaskID                 string `json:"task_id"`
	GrantID                string `json:"grant_id"`
	OwnerRevision          int64  `json:"owner_revision"`
	RetryEpoch             string `json:"retry_epoch"`
	TransactionCompletion  string `json:"transaction_completion"`
	Outcome                string `json:"outcome"`
	Evidence               string `json:"evidence"`
}

// swarmWitnessR3ProtocolID is the protocol stamped by the settlement wrapper.
// The claim bridge keeps its own literal until that wrapper is injected.
var swarmWitnessR3ProtocolID = "r3-ledger-claim-v1"

type probeCaseFixture struct {
	TaskID         string `json:"task_id"`
	GrantID        string `json:"grant_id"`
	OwnerRevision  int64  `json:"owner_revision"`
	RetryEpoch     string `json:"retry_epoch"`
	InitialSpent   bool   `json:"initial_spent"`
}

type probeCase struct {
	CaseID  string            `json:"case_id"`
	Fixture probeCaseFixture  `json:"fixture"`
	Actions []probeCaseAction `json:"actions"`
}

type probeInputFile struct {
	ProtocolID string      `json:"protocol_id"`
	Cases      []probeCase `json:"cases"`
	DBDir      string      `json:"db_dir"`
}

type stepObservation struct {
	ProtocolID      string         `json:"protocol_id"`
	CaseID          string         `json:"case_id"`
	Step            int            `json:"step"`
	Op              string         `json:"op"`
	AdapterID       string         `json:"adapter_id"`
	ExecutionStatus string         `json:"execution_status"`
	Disposition     string         `json:"disposition"`
	Inputs          map[string]any `json:"inputs"`
	NativeResult    map[string]any `json:"native_result"`
	State           map[string]any `json:"state"`
	Notes           string         `json:"notes"`
}

// TestSwarmWitnessR3Probe is the anchored opt-in probe (build tag required).
func TestSwarmWitnessR3Probe(t *testing.T) {
	casesPath := os.Getenv("SWARM_WITNESS_R3_CASES")
	outPath := os.Getenv("SWARM_WITNESS_R3_OUT")
	if casesPath == "" || outPath == "" {
		t.Fatalf("SWARM_WITNESS_R3_CASES and SWARM_WITNESS_R3_OUT are required")
	}
	raw, err := os.ReadFile(casesPath)
	if err != nil {
		t.Fatalf("read cases: %v", err)
	}
	var input probeInputFile
	if err := json.Unmarshal(raw, &input); err != nil {
		t.Fatalf("parse cases: %v", err)
	}
	if input.ProtocolID != "r3-ledger-claim-v1" && input.ProtocolID != "r3-ledger-settlement-v1" {
		t.Fatalf("unexpected protocol_id %q", input.ProtocolID)
	}
	swarmWitnessR3ProtocolID = input.ProtocolID
	if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
		t.Fatalf("mkdir out: %v", err)
	}
	out, err := os.Create(outPath)
	if err != nil {
		t.Fatalf("create out: %v", err)
	}
	defer out.Close()

	enc := json.NewEncoder(out)
	for _, cse := range input.Cases {
		obs, runErr := runProbeCase(t, input.DBDir, cse)
		for _, row := range obs {
			if err := enc.Encode(row); err != nil {
				t.Fatalf("encode: %v", err)
			}
		}
		if runErr != nil {
			// Preserve partial observations; do not hide counterexamples.
			t.Logf("case %s ended with: %v", cse.CaseID, runErr)
		}
	}
}

func runProbeCase(t *testing.T, dbDir string, cse probeCase) ([]stepObservation, error) {
	t.Helper()
	dir := filepath.Join(dbDir, cse.CaseID)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	dbPath := filepath.Join(dir, "case.sqlite")
	// The disposable-tree bridge expects host helpers from the pinned
	// owner-witness fixture. When those helpers are unavailable in this
	// injection, emit completed observations with disposition unsupported
	// so the comparator stays fail-closed rather than inventing decisions.
	if !swarmWitnessR3NativeReady() {
		var rows []stepObservation
		for _, act := range cse.Actions {
			rows = append(rows, stepObservation{
				ProtocolID:      "r3-ledger-claim-v1",
				CaseID:          cse.CaseID,
				Step:            act.Step,
				Op:              act.Op,
				AdapterID:       "bmo_l1_first_edit",
				ExecutionStatus: "missing",
				Disposition:     "unsupported",
				Inputs:          actionInputs(act),
				NativeResult: map[string]any{
					"reason": "native_owner_witness_fixture_helpers_unavailable",
					"db":     dbPath,
				},
				State: nil,
				Notes: "Bridge compiled but host fixture setup hooks are not linked; refusing to invent L1 outcomes",
			})
		}
		return rows, fmt.Errorf("native fixture helpers unavailable")
	}
	return runNativeProbeCase(t, dbPath, cse)
}

func actionInputs(act probeCaseAction) map[string]any {
	if act.Op != "claim_first_edit" {
		return map[string]any{}
	}
	tx := act.TransactionCompletion
	if tx == "" {
		tx = "commit"
	}
	return map[string]any{
		"call_id":                 act.CallID,
		"task_id":                 act.TaskID,
		"grant_id":                act.GrantID,
		"owner_revision":          act.OwnerRevision,
		"retry_epoch":             act.RetryEpoch,
		"transaction_completion":  tx,
	}
}

// swarmWitnessR3NativeReady reports whether this BMO tree has the probe's
// fixture wiring. Default false keeps honesty when only the bridge file is
// present without the companion fixture helpers.
func swarmWitnessR3NativeReady() bool {
	return swarmWitnessR3FixtureReady()
}

// Overridden in bmo_adapter_fixture.go when fixture helpers are injected.
var swarmWitnessR3FixtureReady = func() bool { return false }

func runNativeProbeCase(t *testing.T, dbPath string, cse probeCase) ([]stepObservation, error) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	store, cleanup, err := swarmWitnessR3OpenCase(ctx, dbPath, cse.Fixture)
	if err != nil {
		return nil, err
	}
	defer cleanup()

	var rows []stepObservation
	for _, act := range cse.Actions {
		row, err := swarmWitnessR3Apply(ctx, store, cse, act)
		rows = append(rows, row)
		if err != nil && row.ExecutionStatus == "failed" {
			return rows, err
		}
	}
	return rows, nil
}

// The following symbols are provided by the companion fixture file
// (bmo_adapter_fixture.go) when the disposable tree is prepared:

type swarmWitnessR3Store interface {
	ClaimOrdinaryRetainedGrantFirstEditTx(ctx context.Context, tx *sql.Tx, epoch any, receipt any) error
}

var swarmWitnessR3OpenCase = func(ctx context.Context, dbPath string, fixture probeCaseFixture) (any, func(), error) {
	return nil, func() {}, fmt.Errorf("fixture open not linked")
}

var swarmWitnessR3Apply = func(ctx context.Context, store any, cse probeCase, act probeCaseAction) (stepObservation, error) {
	return stepObservation{
		ProtocolID:      "r3-ledger-claim-v1",
		CaseID:          cse.CaseID,
		Step:            act.Step,
		Op:              act.Op,
		AdapterID:       "bmo_l1_first_edit",
		ExecutionStatus: "missing",
		Disposition:     "unsupported",
		Inputs:          actionInputs(act),
		NativeResult:    map[string]any{"reason": "apply_not_linked"},
		State:           nil,
		Notes:           "apply hook not linked",
	}, fmt.Errorf("apply not linked")
}
