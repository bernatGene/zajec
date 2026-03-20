---
name: write-plan
description: Creating PLAN.md files to track complex multi-step tasks, current state, and next steps
---

## When to Use

Use this skill when:

- Mostly only when asked to. 
- Starting a complex feature that spans multiple files/layers
- Context is getting too long and needs to be summarized
- Switching from one phase of work to another
- You need to hand off or resume work later

## Plan File Structure

Create `PLAN_{FEATURE_NAME}.md` in the project root:
(you need to have write permission. If in plan mode, don't attempt to go looking for
other directories.)

```markdown
# {Feature Name} Plan

## Current State

### Completed

List completed items with brief descriptions

### In Progress / Next Steps

List what is pending or in progress

---

## Objective

Clear one-sentence description of the goal.

## Implementation Details

### Section 1: {Topic}

**Current:** What is done
**Next:** What is needed
**Files:** List affected files

### Section 2: {Topic}

...

## Open Questions

- Question 1?
- Question 2?

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2
```


## Integration with Other Skills

- After creating a plan, use `db-ops` if migrations are needed
- Reference `api-development` when planning endpoint structure
- Use `geospatial` when planning GIS-related features

