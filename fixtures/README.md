# Fictional inputs and independent expectations

The supplied `seed.json`, `domain.md`, and `expected-seed-results.json` are unchanged.
`scripts/make_fixtures.py` deterministically copies the seeds and adds Q9, a two-document
question. Its explicit billing topic routes to the supplied Billing reviewer.
`expected.json` was specified by source inspection before generating model responses.
No random seed is used. No application answers are used as the answer key.

The scenario files are labelled simulations of source updates, not additional original
product rules. The alternate support document deliberately introduces an unresolved
contradiction. The metadata-removal case deliberately leaves ambiguous authority.
They test review invalidation; they do not establish changed policies as approved truth.
