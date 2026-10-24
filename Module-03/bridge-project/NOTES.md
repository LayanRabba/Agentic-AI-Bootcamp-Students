# Module 3 Bridge Project — NOTES

## a. Where did the budget force a real trade-off?

The system had a maximum budget of nine GLEIF lookups for seven suppliers. Mandatory OFAC screening was performed separately and was not counted against the lookup budget.

I prioritized suppliers according to risk and ambiguity. Siemens AG received additional searches because the register returned multiple related companies without an exact legal-name match. Almarai Company also received an additional search to investigate its missing LEI record.

The trade-off was postponing the GLEIF identity lookup for **C & V Works ApS**, the lowest-priority supplier in the plan. Instead of presenting an unverified supplier as safe, the agent returned **INSUFFICIENT** and explicitly reported the missing verification in the memo.

The final run used exactly **9 of 9 GLEIF lookups**.

## b. What sanctions threshold did I choose, and why?

I used a similarity threshold of **0.93** to flag high-risk OFAC matches for investigation, with exact normalized-name matches handled separately.

During testing, **Al Wasel and Babel General Trading LLC** returned a similarity score of **1.00** against an OFAC-listed name under the **IRAQ2** programme. The final prototype classified this case as **REJECT** and instructed Rana not to release payment.

Other suppliers had substantially lower similarity scores, including examples around 0.71–0.81. These scores alone were not treated as evidence that the suppliers were sanctioned.

A lower threshold would risk false positives and unnecessarily delayed payments. A higher threshold could miss relevant spelling variations or aliases, potentially leading to a prohibited payment.

Fuzzy name similarity is not definitive proof of legal identity; a real compliance process would require identity confirmation and review.

## c. Where did my agent nearly get it wrong?

During the initial test, **Al Wasel and Babel General Trading LLC** received **CONDITIONS**, despite an exact normalized-name match with an OFAC-listed entry scoring 1.00 under IRAQ2.

This exposed a weakness in the initial decision logic: it treated all high-similarity sanctions matches as cases requiring conditions, without distinguishing the exact-name case.

I revised the decision logic to classify the exact-name case as REJECT in this educational scenario while retaining the underlying match evidence for review.

I also improved the workflow to use the limited lookup budget more deliberately. The initial version used seven GLEIF lookups, while the revised version used nine and disclosed the supplier whose identity lookup was postponed.

## Repeated-run comparison

I ran the revised agent twice.

Both runs produced the same seven verdicts:

| Supplier | Verdict |
|---|---|
| Al Wasel and Babel General Trading LLC | REJECT |
| Siemens AG | CONDITIONS |
| Zorblax Trading FZE | INSUFFICIENT |
| Al Noor Cart Trading Company | APPROVE |
| Almarai Company | CONDITIONS |
| Maersk A/S | APPROVE |
| C & V Works ApS | INSUFFICIENT |

The exact memo text differed between the runs, particularly in the explanations for Al Wasel, Siemens AG, Almarai Company, and C & V Works ApS. However, the verdicts and lookup count remained stable.

This demonstrates that language-model-generated