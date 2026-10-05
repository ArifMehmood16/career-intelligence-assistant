# Decisions from existing source

- Verdict already exposes verdict label, nullable requirementScore, three 0–4
  dimension ratings and stored evidence. Filter the overall requirement percentage
  by default; clarification was offered, with no scoring-policy change.
- VerdictsPanel currently maps every card without controls. Extract this section
  rather than refetching or changing APIs. Existing ComparePanel native controls
  establish the visual pattern; useId gives unique accessible labels.
- Source RoleAnalysisV2 indexes CV/advert concurrently, performs hybrid retrieval,
  bounded judging/correction and domain aggregation. V2JobRunner locks publication;
  worker jobs live in SQL and now expire during operation. Diagrams show these paths.
- Screenshots must use synthetic /dev/states fixtures. Earlier maintainer screenshots
  are historical; new captures explicitly document synthetic provenance.
