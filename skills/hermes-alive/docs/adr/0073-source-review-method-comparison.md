# ADR 0073 — Compare review methods and audit the evaluator's labels

Status: bounded diagnostic completed; no demonstrated method improvement or gate qualification.

## Predeclared diagnostic and actual results

Eight authored public synthetic cases covered cross-language compression, a grounded
tentative suggestion, an explicit broad-benefit guarantee, historical relative time,
invented completed action, attribution binding, source prompt injection and conflicting
source dates. The existing method matched all eight recorded expectations. These are
author expectations withheld from the model, not independent human gold or real user
benefit. Success does not cancel the earlier retained-draft disagreement.

Then fixed four candidates and evidence snapshots for a paired baseline versus
claim/evidence-inventory method comparison, alternating method order. The first
candidate is exactly the previously retained generated text, with the exact original
source excerpt; its interests/detail preference/advice values were carried into a
reconstructed diagnostic envelope. That envelope is not claimed identical to the
earlier encrypted review snapshot. The other three candidates are authored diagnostic
contrasts, NOT regenerated outputs or proof of generator improvement.

All sixteen calls actually returned `claude-haiku-4-5` / `custom:ustc`, sixteen HTTP
200 responses, no provider/contract failures. In the paired four-case study each method
accepted both grounded positive examples, rejected the clear compatibility/suitability
leap and accepted the retained disputed zero-loss ending. Each therefore disagreed
with one of its four preregistered expectations. No superiority was demonstrated.

The revised reviewer explicitly considered the ending and interpreted it as a
cautious recommendation rather than a guarantee. This contradicts the assumption
that the reviewer simply skipped the closing sentence. It does NOT prove that the
reviewer is right; nor does an author-set label prove it wrong. Prior ADRs called this
an unsupported assurance. Preserve that history and the old label, but now treat
the criterion and pragmatic scope as an unresolved calibration question rather than
an independently established safety failure. No label was silently flipped to obtain
a clean score. No additional paid regeneration/retry followed.

## Runtime decision

Do not install a longer prompt as the default merely because it looks more rigorous.
The baseline remains the shadow runtime default; the unproven claim-inventory method
lives only in the diagnostic probe for reproducible future comparisons. Review events
now bind a prompt digest across start/completion/current verification, preventing
reuse after a method change. Invalid findings remain unresolved. Delivery authority
is still false, and the support component is not an admitted production send gate.

The live reports' historical metric `unsafe_acceptances` actually counts acceptances
against authored negative labels. It is not an observed unsafe delivery. Future probe
reports name this `authored_unsupported_acceptances`; historical reports/raw outputs
remain unchanged. Changing the metric's name does not erase the two disagreements.

## Research and revised next step

[FActScore](https://arxiv.org/abs/2305.14251) decomposes factual information into atomic
facts checked against a knowledge source. [SAFE's official implementation](https://github.com/google-deepmind/long-form-factuality/blob/main/eval/safe/README.md)
uses fact-level search-enabled evaluation. Neither is evidence that a single overall
model verdict proves our communication is correct or useful.

[VERISCORE](https://arxiv.org/abs/2406.19276) specifically distinguishes verifiable and
unverifiable content across diverse generation tasks; its abstract cautions against
assuming every claim is verifiable. Our inference: Alive's natural mixed-purpose
messages need material factual claims distinguished from cautious recommendations,
opinion and conversational framing, not a requirement to literally prove every phrase.
This is a direction to test, not borrowed benchmark scores or our implemented result.

Next build claim-level, context-sensitive evidence accounting with independently
defensible labels and held-out mixtures of grounded facts, ambiguity, false claims
and useful suggestions. Evaluate extraction coverage and support separately: a
well-formed whole-message verdict cannot show which claim was missed or interpreted
pragmatically. Preserve source caveats and uncertainties that could materially mislead;
do not ban ordinary conversational language or declare every colloquial assurance a
material factual failure without adjudicating its context. Do not ask the user to
babysit each sentence or acquire a third provider/key as an installation condition.

Still required: usable intent/expression admission through current policy, authorized
dispatch and attributed outcomes; actual continuous agenda/learning/user benefit;
memory retention/forgetting/migration; full install/upgrade/reinstall/data/auth safety
and production canary. A factuality pilot is not a substitute for that complete loop.
