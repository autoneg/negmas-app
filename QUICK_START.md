# Quick Start - Tournament Navigation Testing

## Start the App

```bash
negmas-app run
```

Opens at: **http://127.0.0.1:5174**

---

## 5-Minute Quick Test

### 1. Create Tournament (2 min)
1. Click **Tournaments** tab
2. Click **New Tournament** button
3. Select 2 competitors (e.g., AspirationNegotiator, MiCRO)
4. Select 2 scenarios
5. Click **Start Tournament**

**✅ Expected**: Grid shows blue cells → green when done

### 2. View Running Negotiation (1 min)
1. Scroll to **Negotiations** panel (bottom)
2. Click on any negotiation row

**✅ Expected**:
- Breadcrumb: "Tournament > Negotiation #1"
- Badge: "From Tournament" 🏆
- Back button: "Tournament"
- All panels show data

### 3. Navigate Back (30 sec)
1. Click **Tournament** button (top left)

**✅ Expected**: Returns to tournament, grid still visible

### 4. Load Saved Tournament (1 min)
1. Go to **Tournaments** tab
2. Click **Saved Tournaments** in sidebar
3. Select any tournament
4. Click **View** on any negotiation

**✅ Expected**: Same as step 2 (breadcrumb, badge, panels)

### 5. Navigate Back Again (30 sec)
1. Click breadcrumb **Tournament** link

**✅ Expected**: Returns to saved tournament

---

## If Everything Works ✅

You should see:
- ✅ Tournaments run and update live
- ✅ Grid cells change color (blue → green/yellow/red)
- ✅ Leaderboard updates with rankings
- ✅ Clicking negotiation opens viewer
- ✅ Breadcrumb shows context
- ✅ Back button returns to tournament
- ✅ All panels work (history, 2D plot, timeline, etc.)
- ✅ No errors in browser console (F12)

**Status**: Production Ready! 🎉

---

## If Something Breaks ❌

1. Check browser console (F12) for errors
2. Check `TESTING_GUIDE.md` for troubleshooting
3. Try with smaller tournament (1 competitor, 1 scenario)
4. Verify backend is running on port 8019
5. Verify frontend served from port 5174

---

## Key Features to Notice

### Visual Elements
- **Grid cells**: Blue (running) → Green (✓ agreement)
- **Leaderboard**: Top 3 have medals 🥇🥈🥉
- **Breadcrumb**: Shows "Tournament > Negotiation #X"
- **Badge**: Trophy icon 🏆 "From Tournament"
- **Progress bar**: Animates during tournament
- **LIVE indicator**: Pulses red dot

### Navigation Flow
```
Tournament List
    ↓
Single Tournament (Grid + Leaderboard + Negotiations)
    ↓ (click negotiation)
Negotiation Viewer (with breadcrumb)
    ↓ (click back)
Single Tournament (state preserved)
```

---

## Commands Reference

```bash
# Start app
negmas-app run

# Kill servers
negmas-app kill

# Restart
negmas-app restart

# Build frontend
cd src/frontend && npm run build

# Run tests
cd src/frontend && npm test -- --run
pytest tests/ -v
```

---

## Documentation Files

- **TESTING_GUIDE.md** - Comprehensive testing checklist
- **DEPLOYMENT_READY.md** - Production deployment info
- **SESSION.md** - Implementation details
- **TASKS.md** - Feature status
- **AGENTS.md** - Build commands

---

## Success Criteria

✅ All features work as expected  
✅ No errors in console  
✅ Smooth animations and updates  
✅ Navigation flows correctly  
✅ All panels render with data  

**If all checked**: Ready for production! 🚀

---

**Time to Test**: ~5-10 minutes  
**Expected Result**: Everything works perfectly ✨
