//go:build swarm_witness_r3

package sessioncompaction

// Companion fixture hooks for the disposable-tree bridge.
//
// When this file is copied into a pinned BMO checkout together with
// bmo_adapter_test.go, replace the stub bodies below with the minimal
// owner-witness setup extracted from
// ordinary_retry_retained_grant_owner_witness_test.go at pin
// 4b717d793f68dc1a467f6ff4e3ca24d93c8ebfbe.
//
// Required native call (AC1): ClaimOrdinaryRetainedGrantFirstEditTx on a real
// AdmissionStore transaction. Do not use OrdinaryRetryRetainedGrantShapeEligible
// as the admission result. Spent status must be derived from authoritative
// claim/transfer readback, not the predecessor admission consumed flag.
//
// Until those hooks are linked against a real BMO tree, swarmWitnessR3FixtureReady
// remains false and the probe emits execution_status=missing (fail-closed).

func init() {
	swarmWitnessR3FixtureReady = func() bool {
		// Flip to true only after open/apply hooks call real L1 methods.
		return false
	}
}
