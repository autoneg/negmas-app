# NegMAS App - Known Issues

## High Priority

### Negotiations Management
- [ ] Add running/completed negotiations table view
- [ ] Click table row to open negotiation with all panels

### Tournament Feature
- [ ] Design tournament models and config (based on cartesian_tournament)
- [ ] Implement tournament service
- [ ] Create tournament UI (scenarios, competitors, params)
- [ ] Add tournament results display (scores, details)

## Medium Priority

### Panel Layout Issues
- [ ] Panels should be collapsible
- [ ] Each panel should take all available space (when collapsing one, others expand)
- [ ] Log panel should auto-scroll
- [ ] Results panel should only appear at the end of negotiation
- [ ] Results panel appears under log instead of under 2D graph (wrong position)
- [ ] Utility Timeline should be under 2D Utility View (currently wrong order)
- [ ] Panel controls don't disappear when deselected in start wizard

## Low Priority

(none yet)

---

## Completed

- [x] Research negmas.genius module for bridge API
- [x] Add Genius Bridge status indicator to header
- [x] Create backend API endpoint for bridge status/control
- [x] Add JS functions for bridge control in Alpine app
- [x] Add CSS for bridge status indicator
- [x] Auto-start bridge when selecting Genius agent
- [x] Fix NaiveTitForTatNegotiator bug (was negmas bug in ExpDiscountedUFun.minmax() not using self.outcome_space)
- [x] Test the Genius bridge feature
- [x] Commit Genius bridge changes
- [x] Add Typer CLI with --port, --host, --reload, --log-level options
- [x] Add dynamic mechanism registry (SAO, TAU, GB, VetoST, HillClimbingST)
- [x] Agent names default to type name + index (Aspiration1, Boulware2)
- [x] Fix zoom panels showing nothing
