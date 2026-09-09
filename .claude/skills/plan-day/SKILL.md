---
name: plan-day
description: Create or update a day plan via IDM MCP tools with consistent formatting and the end-of-day ritual (deployment slot, next-day planning, learning capture). Use when the user asks to "plan tomorrow", "create day plan", "EOD", "end of day", or is creating/updating items via `mcp__idm__create_day_plan_item`.
---

# Plan Day

## WHY
Day plans created via IDM MCP tools (`mcp__idm__create_day_plan_item`, `mcp__idm__get_day_plan`) need consistent formatting and a reliable end-of-day ritual so nothing falls through the cracks — deployment prep, next-day planning, and learning capture.

## Item Format

Every item created via `mcp__idm__create_day_plan_item` uses this text format:

```
[HH:MM AM - HH:MM AM/PM] - Task title
```

Session assignment: items before 1:00 PM use `morning`, 2:00 PM onward use `afternoon`. The 1:00-2:00 PM slot is lunch (fixed, not assignable).

## Morning Session

Fully flexible. Populated during next-day planning (see below) or on user request. No fixed slots.

## EOD Block (5:30 PM - 7:00 PM)

Always included in the afternoon session. Three fixed slots, always in this order:

| Slot | Rule |
|---|---|
| `[5:30 PM - 6:00 PM] - <Feature Name> - Prod Deployment` | Ask user what's being deployed today. One slot per feature — if 2 deployments, split time equally (e.g., `[5:30 - 5:45]` + `[5:45 - 6:00]`) |
| `[6:00 PM - 6:30 PM] - Next-day planning` | Ask user what goes live tomorrow, then draft tomorrow's plan |
| `[6:30 PM - 7:00 PM] - Learning points` | Capture today's learnings via `mcp__idm__add_learning` |

Include the EOD block every day including Fridays — weekend planning is useful for Monday prep.

## Next-Day Planning (during 6:00 PM slot)

When the user asks to plan the next day:

1. **Ask** what features, PRs, or tasks will be live or in progress tomorrow
2. **Draft** the plan based on their answers — morning slots for feature work, afternoon for continuation
3. **Always append** the EOD block to the afternoon session
4. **Create** items via `mcp__idm__create_day_plan_item` with the format above

Do not pre-fill the next day's plan without asking — the user decides what goes on it.

## Task Arrangement

Arrange tasks contiguously. Place shorter tasks at slot edges to avoid splitting longer tasks across non-contiguous slots.

## When This Skill Applies

- Creating or updating day plan items via IDM MCP tools
- User asks to "plan tomorrow", "create day plan", "EOD", or "end of day"
- Session is ending past 5:00 PM and no EOD block exists for today — suggest creating one
