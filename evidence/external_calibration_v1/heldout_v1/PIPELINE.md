# Held-out inference pipeline

The comparison uses the frozen 70-packet eligibility set and the retained assessor labels. It does not add cases. False-exclusivity packets stay in the denominator.

Raw Swarm Witness and the raw invariant checker abstain on all 70 packets. Decisive coverage of the 36 assessor-decisive labels is 0/36. Unsupported support and unsupported refutation are 0. Each arm reads 332 supplied records and makes 0 additional source requests.

The same qualified adapter, `composed_observations`, is then given to each method. Both adapted arms recover 36/36 of those assessor-decisive labels, abstain on the other 34, and add 0 unsupported supports or refutations against the assessor. The separate warrant is decisive on 26 of the 70 packets. Against that warrant the adapted arms are 26/26 correct and have 10 unsupported supports. The adapter emits 36 derived records from the supplied packets and makes 0 additional source requests. On every packet the adapted verdict equals the adapter verdict, and the two adapted arms agree, so the result does not support a Swarm Witness-specific superiority claim. `transfer_claim` and `superiority_claim` stay false.

Thirteen false-exclusivity packets remain. Ten of them have an assessor label of supported and a separate warrant of unresolved. The raw arms abstain on those ten. The adapted arms support them. Against the assessor label that support is inside the 36 recovered judgments. Against the separate warrant it is unsupported support. Those ten rows are retained in `pipeline_v1.json`.
