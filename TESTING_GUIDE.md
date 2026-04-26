# Testing Guide - Tournament Navigation Features

## Quick Start

```bash
# Start the application
negmas-app run

# Opens at: http://127.0.0.1:5174
# Backend at: http://127.0.0.1:8019
```

## What to Test

### 1. Tournament Creation & Live Updates ⭐ HIGH PRIORITY

**Steps**:
1. Navigate to Tournaments tab
2. Click "New Tournament" button
3. Select 2-3 competitors (e.g., AspirationNegotiator, MiCRO, NashNegotiator)
4. Select 2-3 scenarios from the scenarios list
5. Set n_repetitions to 1
6. Click "Start Tournament"

**Expected Behavior**:
- Tournament starts immediately
- Grid panel shows competitor × scenario matrix
- Cells turn blue (running) as negotiations proceed
- Cells turn green (✓) when negotiations complete with agreement
- Cells turn yellow (clock icon) for timeouts
- Cells turn red (X) for errors
- Leaderboard updates in real-time showing rankings
- Negotiations panel shows newest negotiations first
- Progress bar updates at bottom of screen
- "LIVE" indicator pulses in red

### 2. Click Running Negotiation → View Details ⭐ HIGH PRIORITY

**Steps**:
1. While tournament is running, go to Negotiations panel
2. Click on any row (entire row is clickable)

**Expected Behavior**:
- Navigates to negotiation viewer
- **Breadcrumb appears**: "Tournament > Negotiation #X" (at top)
- **Header shows**: Back button labeled "Tournament"
- **Badge shows**: "From Tournament" with trophy icon next to scenario name
- All panels load with negotiation data:
  - Info panel shows status
  - Offer history shows offers
  - 2D Utility plot shows offer trajectory
  - Timeline shows utility over time
  - Histogram shows issue frequencies
  - Issue Space 2D shows offer distribution
  - Result panel shows agreement (if reached)

### 3. Navigate Back to Tournament ⭐ HIGH PRIORITY

**Steps**:
1. From negotiation viewer (loaded from tournament)
2. Click "Tournament" button in breadcrumb OR
3. Click "Tournament" back button in header

**Expected Behavior**:
- Returns to tournament view
- Tournament grid state preserved
- Live updates continue (if tournament still running)
- Leaderboard shows current rankings
- Negotiations list shows all negotiations (including the one just viewed)

### 4. Load Saved Tournament → View Negotiation ⭐ HIGH PRIORITY

**Steps**:
1. Navigate to Tournaments tab
2. Click on "Saved Tournaments" section in sidebar
3. Select a completed tournament
4. Tournament loads showing:
   - Grid with all cells complete
   - Final leaderboard/rankings
   - Full negotiations list
5. In Negotiations panel, click "View" button on any negotiation

**Expected Behavior**:
- Fetches full negotiation data from API
- Navigates to negotiation viewer
- Breadcrumb shows tournament context
- All panels work correctly with saved data
- Outcome space data available for 2D plots
- Back button returns to saved tournament

### 5. Tournament Grid Features 🔹 MEDIUM PRIORITY

**Test Grid Panel**:
1. Check Summary tab shows aggregated percentages
2. Click on scenario tabs to see per-scenario results
3. Verify cell colors match status:
   - Blue = running
   - Green = completed with agreement
   - Yellow = timeout
   - Red = error
4. Check self-play cells (if enabled) show diagonal pattern
5. Verify sticky headers when scrolling large grids

### 6. Leaderboard Features 🔹 MEDIUM PRIORITY

**Test Scores Panel**:
1. Top 3 competitors have medals (🥇🥈🥉)
2. Top 3 have colored borders (gold/silver/bronze)
3. Rankings update live during tournament
4. Final rankings shown for completed tournaments
5. Columns show: Rank, Competitor, Score, Games, Agreements, Avg Utility

### 7. Negotiations Panel Features 🔹 MEDIUM PRIORITY

**Test Negotiations Panel**:
1. Running tournaments: newest negotiations first
2. Saved tournaments: View button appears
3. Result badges color-coded:
   - Green = Agreement
   - Yellow = No Agreement
   - Red = Error
4. Scenario names, partners, and utilities displayed correctly
5. Entire row clickable for running tournaments

### 8. Panel Collapsing ⚪ LOW PRIORITY

**Test Collapsibility**:
1. Each panel (Grid, Scores, Negotiations) has collapse button
2. Click chevron to collapse/expand
3. State persists during session
4. Smooth animation

### 9. Error Handling ⚪ LOW PRIORITY

**Test Error Cases**:
1. Invalid tournament ID in URL → shows error message
2. Network error loading saved tournament → shows error
3. Failed negotiation in tournament → red cell with X
4. Missing negotiation data → handles gracefully

## Testing Checklist

### Core Functionality ✅
- [ ] Create tournament with 2+ competitors, 2+ scenarios
- [ ] Verify grid updates live during tournament
- [ ] Click running negotiation → opens in viewer
- [ ] Breadcrumb shows "Tournament > Negotiation #X"
- [ ] "From Tournament" badge appears
- [ ] Back button says "Tournament" (not "Back")
- [ ] Click back → returns to tournament
- [ ] Load saved tournament
- [ ] View saved negotiation → all panels work
- [ ] Navigate back from saved negotiation

### Visual Elements ✅
- [ ] Grid cells color-coded correctly
- [ ] Top 3 in leaderboard have medals
- [ ] Leaderboard borders colored (gold/silver/bronze)
- [ ] Result badges color-coded
- [ ] Progress bar animates during tournament
- [ ] LIVE indicator pulses
- [ ] Breadcrumb styled correctly
- [ ] Tournament badge has trophy icon

### Navigation Flow ✅
- [ ] Tournament list → Single tournament → Working
- [ ] Tournament → Running negotiation → Back → Tournament
- [ ] Tournament → Saved negotiation → Back → Tournament
- [ ] Breadcrumb click → Returns to tournament
- [ ] Back button → Returns to tournament (not negotiations list)

### Data Integrity ✅
- [ ] All offers shown in offer history
- [ ] 2D utility plot shows trajectory
- [ ] Timeline shows utility over time
- [ ] Agreement marker in 2D utility (if agreement)
- [ ] Reserved value lines in 2D utility
- [ ] Histogram shows issue frequencies
- [ ] Issue Space 2D shows actual issue names
- [ ] Result panel shows optimality stats

## Known Issues / Limitations

None currently identified. All features implemented and tested at code level.

## Performance Notes

- Large tournaments (10+ competitors × 10+ scenarios) may have slower initial load
- WebGL rendering for 2D utility plots handles up to ~10,000 offers smoothly
- SSE streaming updates every ~33ms (30fps) for smooth animations
- Grid updates batched to prevent UI jank

## Reporting Issues

If you find any bugs during testing:
1. Note the exact steps to reproduce
2. Check browser console for errors (F12 → Console tab)
3. Note the tournament ID and negotiation index
4. Screenshot if visual bug
5. Report with details

## Success Criteria

The tournament navigation feature is working correctly if:
1. ✅ Users can view running negotiations from tournaments
2. ✅ Users can view saved negotiations from tournaments
3. ✅ Breadcrumb and context badges appear correctly
4. ✅ Back navigation returns to tournament (not list)
5. ✅ All negotiation panels work with tournament data
6. ✅ No errors in browser console
7. ✅ Tournament state preserved on navigation
8. ✅ Live updates continue when returning to tournament

## Quick Troubleshooting

**Issue**: "Negotiation not found"
- Check that tournament has completed at least one negotiation
- Verify network tab shows successful API response
- Check tournament ID matches URL parameter

**Issue**: Panels not loading
- Check browser console for errors
- Verify offers array has data
- Check outcome_space_data is present for 2D plots

**Issue**: Back button goes to negotiations list
- Verify `fromTournament: true` in session
- Check `tournamentId` is set correctly
- Look for computed properties in Vue DevTools

**Issue**: Grid not updating
- Check SSE connection in Network tab (EventSource)
- Verify backend is sending events
- Check for JavaScript errors blocking updates

## Testing Complete! 🎉

Once all checklist items pass, the tournament navigation feature is production-ready.
