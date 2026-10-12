---
name: review-postmortem
description: Review an incident postmortem for completeness and for follow-ups that actually prevent a repeat. Use when the user shares or asks about a postmortem, incident write-up or RCA draft.
---

# Review a postmortem

Input: a postmortem draft (path or pasted text). Read it fully. Report what is missing or weak, each with the sentence or section it concerns and a concrete fix.

## Check
- **Summary and impact:** what failed, who was affected, for how long, how severe. Numbers, not adjectives.
- **Timeline:** timestamped, from the change or trigger through detection, mitigation and resolution; no unexplained gaps.
- **Detection:** how it was noticed and how long that took. If a customer noticed first, say so.
- **Cause:** the trigger is separated from the root cause and from contributing factors. Flag a single-cause story for a multi-step failure, and a "human error" root cause (ask what allowed the error).
- **Follow-ups:** each has an owner, a due date, and a type (prevent, detect or mitigate). Flag vague items ("be more careful", "improve monitoring") and items with no owner.
- **Ratchet:** for each root cause, which deterministic check would have caught it, such as a lint rule, test, alert, hook or an entry in `standards/rules/`? If the answer is "none", the follow-up should create one.
- **Blameless tone, and hygiene:** no blame on individuals; no secrets, tokens or personal data pasted into the document.

## Output
`Missing`, `Weak`, `Ratchet candidates` (proposed new checks or rules, each with the check type it would use). Zero findings is a valid result. Do not edit the postmortem.
