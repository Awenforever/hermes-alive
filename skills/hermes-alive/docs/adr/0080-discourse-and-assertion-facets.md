# ADR 0080 — Discourse function must not exempt embedded assertions

Status: opt-in facet representation implemented; actual semantic improvement
unproven because both bounded live reviewer experiments timed out.

## Recorded issue

ADR 0074's real claim-accounting output classified the compound closing sentence
as a recommendation with not_applicable support. Its own explanation said the
no-signup/no-cost premise echoed the source, but that premise had no independently
checked ledger entry. Whether the ordinary phrase "nothing is lost" is a literal
guarantee remains a pragmatic ambiguity, not an independently settled gold label.
An exclusive main-role label can obscure embedded facts regardless of that dispute.

## Orthogonal representation

FacetedClaimSupportReviewer is opt-in, not the default reviewer or an automatic
delivery gate. Ordered exact discourse segments track statement, recommendation,
question or social function. A separate material-assertion ledger tracks each
proposition's exact anchor, asserted/tentative epistemic role, support, references
and limitations. Overlapping anchors allow several propositions within a compound
phrase; a segment links its assertions without forcing an artificial line split.

Every recorded assertion is independently evaluated using the same quotation,
evidence-field and epistemic checks as existing claim accounting. A recommendation
or social label cannot supply not_applicable for an assertion. Learned advice still
cannot establish a factual user profile. Orphan assertions, missing anchors,
unsupported references, duplicate identities and incomplete lexical coverage fail.
The host aggregates assertion support independently of discourse function. A model
declaring uncertain extraction produces uncertainty, not a fully supported verdict.

This does not prove extraction completeness or source entailment. A model can
still omit a claim and declare its scan complete. Tests explicitly preserve that
counterexample with semantic_coverage_proven=false. There is no keyword blacklist,
per-example repair rule, truth grant or new delivery authority. Independent semantic
qualification remains necessary before this can participate in automatic admission.

## Actual structural evidence

- Local Python 3.14 facets and existing claim/source support suites pass. The new
  fixture keeps the same unsupported completed-action assertion under all four
  discourse labels; changing the main function cannot remove its unsupported status.
  It also exercises encrypted receipt recovery and the no-delivery-authority rule.
- Input tree `41213d0a5d628feaef47e2030742a2bfa3cc5858`, archive SHA256
  `e969943a056dad6105f68472df3aedea6db0456555be7310b66950ac2eaa52aa`.
  Network-none `alive-facets-offline-20261013-r1` exited zero, started
  `2026-10-13T14:34:10.45803352Z`, finished `2026-10-13T14:34:14.829304419Z`.
  Three focused suites pass, log SHA256
  `507f3841b89f88bf65b2913fc3bc9fedad1015c3e47b92234c504af6a5b25412`.
  This is not installation, real semantic accuracy or production qualification.

## Live results: unavailable, not successful

Both experiments used the same retained synthetic/public draft, no regeneration,
private conversation, message send or production model change. They selected two
already configured different-family review lanes, first claude-haiku-4-5, then
claude-sonnet-4-6 in an explicitly named separate experiment. No actual response
model was observed and no review findings were produced. Do not infer model quality
or algorithm accuracy from an unavailable service response.

- First: one logical model call, two observed async HTTP attempts to the USTC host;
  first ReadTimeout, second with no terminal status recorded before outer timeout.
  Outer TimeoutError. Client cancellation is inferred from the bounded wait, not
  an observed upstream terminal result. Container zero is the report harness completion,
  NOT review success. Start `2026-10-13T14:33:03.605934569Z`, finish
  `2026-10-13T14:33:55.127368497Z`. Report SHA256
  `eb998cdad1f07350c931dd2ab55b1d95c5168905df29b8cdc379509da81eb6ea`.
- Second: explicitly `configured-sonnet-20261013`, same one-call/two-HTTP timeout
  pattern. Input tree `7196b27a4eb87c42b373a95aeef6fc7e7f9c731f`, archive SHA256
  `2ae106da6d8cc807d1abac8544e96f79deb4a30305fc374ca108e21ef4034bb5`.
  Start `2026-10-13T14:38:11.543242186Z`, finish
  `2026-10-13T14:39:03.066899747Z`. Report SHA256
  `0825047185fdb940457c8fb860d4e7054bbb43716cb3da643d01f2dac1e3bf22`.
- Read-only synthetic journal audit proves two started, two failed, zero completed
  records for these exact operations. The first failure is retained, not overwritten
  or promoted by the second experiment. Existing 40-second request/50-second total
  boundaries remain unchanged. Cumulative logical calls 43, observed async HTTP 55.
- After both processes were verified terminal, exact temporary model-profile,
  isolated profile config/backup/env export paths were removed; root verification
  confirms all absent. Synthetic reports, journals and logs remain. Production
  credentials/configuration are untouched; production start remains
  `2026-10-11T07:43:25.630569081Z` and running.

## Full goal remains open

Do not repeat named operations or manufacture a clean score by hiding failed
history. Further live semantic experiments need an available configured route and
honest comparison on new/general cases, not a prompt tuned solely for this closing.
Continue qualified automatic admission, authenticated onboarding/feedback ingress,
actual host delivery/outcome attribution, longitudinal agenda/memory/adaptation,
derived-copy forgetting, migration/rollback and portable installation acceptance.
No production deployment, release, real send or ten-call acceptance follows here.
