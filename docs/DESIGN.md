# Design decisions

## Decision 1: Classification taxonomy
There should be three main categories for now: Marketing, spam, and job search. For now, all emails that do NOT fit into any of these categories can be classified with a separate 'miscellaneous' label. 

## Decision 2: What counts as the "last 24 hours"
Gmail's newer_than:1d search operator is day-granular, not hour-granular — worth checking whether that's precise enough for you or whether you need after:/before: with exact epoch timestamps.

## Decision 3: Idempotency
I want a persisten DB that will have summaries of the emails the agent has already seen. This way, IF the agent runs multiple times a day, it does not spend tokens re-reading and re-summarizing the same emails. 

## Decision 4: Digest vs. per-email
I would like for the digest to highlight the different categories with some important notes for each category. For example, I will create a system prompt that describes things I am interested in (for marketing), jobs I am looking for (for the job search), and other general interests of mine (for the misc. category). The spam category will not need a digest.

## Decision 5: Trigger model
I want to both be able to trigger the agent by asking it for a summary, but also by having it run once every 24 hours via a GitHub action.