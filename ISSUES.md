# NegMAS App - Known Issues

## High Priority

### Genius Bridge Feature (IN PROGRESS)
- [ ] Test the Genius bridge feature
- [ ] Commit Genius bridge changes

### LAN100 Negotiation Issue
- [ ] Investigate why LAN100 negotiation cannot run
- [ ] Fix or delete problematic saved settings if needed

## Medium Priority

### Panel Layout Issues
- [ ] Zooming out panels shows nothing
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
