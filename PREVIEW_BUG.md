# CRITICAL: Preview Image Bug Investigation

## Problem Summary
Preview images for negotiations are showing wrong/corrupted data:
1. **Orange "crazy lines"**: Wrong offer traces being displayed
2. **Wrong scenarios**: 23-hour-old negotiations showing completely different scenarios
3. **Negotiation ID shows "Unknown"**: This is a critical clue!
4. Interactive mode works correctly - issue is with preview image caching/loading

## Evidence from Screenshots

### Issue 1: Orange Lines (Image 1)
- Shows "Negotiation Trace" with orange lines/dots
- These are offer traces from a DIFFERENT negotiation
- Interactive version shows correct green/blue traces

### Issue 2: Wrong Scenario (Image 3)
- 23-hour-old negotiation 
- Shows completely wrong 2D utility space
- Title says "2D Utility Space" but data is from different negotiation
- Interactive version (Image 4) shows correct data

### Issue 3: First Scenario Wrong (mentioned)
- "Negotiation ID is still Unknown" - THIS IS THE ROOT CAUSE!
- If ID is undefined, preview URL becomes `/api/negotiation/saved/undefined/preview/utility2d`
- This could serve a cached image from a completely different negotiation

## Root Cause Analysis

### Hypothesis 1: negotiation.id is undefined ✓ LIKELY
**Evidence**:
- User mentioned "Negotiation ID is still Unknown"
- InfoPanel displays `negotiation?.scenario_name || 'Unknown'` at line 80
- If `negotiation.id` is undefined, preview URL is malformed

**Impact**:
- Preview URL: `/api/negotiation/saved/undefined/preview/utility2d`
- Backend might return ANY cached preview or 404
- Browser might cache the wrong image

### Hypothesis 2: Session ID collision
**Evidence**:
- Less likely but possible if IDs are being generated incorrectly
- Could explain why old negotiation (23h ago) shows wrong preview

### Hypothesis 3: Preview images not being regenerated
**Evidence**:
- Interactive mode works correctly
- Preview generation happens in `negotiation_preview_service.py`
- Called from `negotiation_storage.py:159` during save

## Files Involved

### Backend
1. `negmas_app/routers/negotiation.py:617-666`
   - Endpoint: `GET /api/negotiation/saved/{session_id}/preview/{panel_type}`
   - Uses `NegotiationStorageService.get_session_dir(session_id)`
   - Returns cached preview image with 1-year cache header

2. `negmas_app/services/negotiation_storage.py:54-56`
   - `get_session_dir(session_id)` returns `NEGOTIATIONS_DIR / session_id`
   - Simple path construction

3. `negmas_app/services/negotiation_preview_service.py:113-261`
   - `_generate_utility2d_preview()` creates the plot
   - Lines 165-189: Adds orange "Offers" trace
   - Uses session.offers for the trace data

### Frontend
1. `src/frontend/src/components/panels/Utility2DPanel.vue:206-211`
   ```javascript
   const previewImageUrl = computed(() => {
     if (props.compact && props.negotiation?.id && props.negotiation?.source === 'saved') {
       return `/api/negotiation/saved/${props.negotiation.id}/preview/utility2d`
     }
     return null
   })
   ```
   - **CRITICAL**: If `props.negotiation?.id` is undefined, returns null (good!)
   - But need to check if ID is actually being passed correctly

2. `src/frontend/src/views/SingleNegotiationView.vue:233-257`
   - Constructs `negotiation` computed property
   - Line 238: `id: currentSession.value?.id`
   - This should be the session ID

3. `src/frontend/src/views/NegotiationsListView.vue:546-604`
   - `loadPreviewData()` function
   - Line 564-565: Sets `id` and `source` fields
   - Need to verify this is setting ID correctly

## Immediate Actions Needed

### 1. Fix Negotiation ID Display (DONE - commit 0127afb)
- ✅ InfoPanel already shows `negotiation?.id` at line 139
- ✅ Made it clickable to open folder
- ⚠️ BUT: Need to verify ID is actually being set!

### 2. Debug ID propagation
- Add console.log to see what `negotiation.id` actually is
- Check if it's undefined, null, or wrong value
- Trace from store → view → panel

### 3. Verify Preview Generation
- Check if previews are actually being generated during save
- Inspect actual files in `~/negmas/negotiations/{session_id}/`
- Look for `utility2d_preview.webp` (or .png, .jpg, .svg)

### 4. Fix Preview Caching
- Backend returns `Cache-Control: public, max-age=31536000` (1 year!)
- If wrong image is cached, it will persist
- Need cache busting or shorter TTL during development

### 5. Regenerate All Previews
- May need to delete all cached previews and regenerate
- Or add timestamp/hash to preview URLs for cache busting

## Testing Steps

1. **Verify Session ID**:
   ```bash
   # Check if session directories exist and have correct IDs
   ls ~/negmas/negotiations/
   ```

2. **Check Preview Files**:
   ```bash
   # For a specific negotiation, check if preview exists
   ls ~/negmas/negotiations/{session_id}/
   # Should see: utility2d_preview.webp (or png/jpg/svg)
   ```

3. **Verify ID in Frontend**:
   - Open browser console
   - Start/load negotiation
   - Check `negotiation.id` value in SingleNegotiationView
   - Check `negotiation.id` in NegotiationsListView preview mode

4. **Clear Browser Cache**:
   - Hard refresh (Cmd+Shift+R / Ctrl+Shift+F5)
   - Clear all cached images for localhost
   - Verify if images update

## Proposed Fixes

### Fix 1: Add Cache Busting to Preview URLs
```javascript
// In Utility2DPanel.vue
const previewImageUrl = computed(() => {
  if (props.compact && props.negotiation?.id && props.negotiation?.source === 'saved') {
    // Add timestamp to prevent caching issues
    const timestamp = props.negotiation.saved_at || Date.now()
    return `/api/negotiation/saved/${props.negotiation.id}/preview/utility2d?t=${timestamp}`
  }
  return null
})
```

### Fix 2: Reduce Cache TTL in Development
```python
# In negotiation.py
headers = {
    "Cache-Control": "public, max-age=3600" if settings.dev_mode else "public, max-age=31536000"
}
```

### Fix 3: Verify ID is Set
```javascript
// In NegotiationsListView.vue loadPreviewData()
console.log('[Preview] Loading for:', {
  id: fullData.id,
  scenario: fullData.scenario_name,
  source: neg.source
})
```

### Fix 4: Force Preview Regeneration on Save
- Check if preview already exists before generating
- Or always regenerate to ensure freshness
- Add error handling if generation fails

## Next Steps

1. ✅ Document the issue (this file)
2. ⏳ Add debug logging to trace ID propagation
3. ⏳ Verify preview files exist on disk
4. ⏳ Add cache busting to preview URLs
5. ⏳ Test with fresh negotiation
6. ⏳ Clear all cached previews and regenerate

## Status
- **Severity**: CRITICAL - wrong data displayed to users
- **Impact**: All preview images potentially wrong
- **Workaround**: Users can click "View Interactive" to see correct data
- **ETA**: Need investigation before fix
