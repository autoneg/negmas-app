# Component Refactoring Plan: Reusable Selectors

## Goal
Extract the search/filter/list functionality from ScenariosView and NegotiatorsView into reusable components that can be used in both explorer views and modal dialogs (NewNegotiationModal, NewTournamentModal).

## Analysis of Current Implementation

### ScenariosView Pattern
**Structure**: Search → Source Filter → Range Filters (Outcomes, Opposition, Rational Fraction) → Grid/List Display

**Key Features**:
- Text search (debounced)
- Source dropdown filter
- 3 range filters (min/max inputs)
- Grid layout with cards
- Selection handling (single select)
- Info panel on right side

### NegotiatorsView Pattern
**Structure**: Search → Source Filter → Group Filter → Mechanism Filter → Available-Only Checkbox → List Display

**Key Features**:
- Text search (debounced)
- Source dropdown filter
- Group dropdown filter
- Mechanism dropdown filter
- Available-only checkbox
- List layout with items
- Selection handling (single select)
- Details panel on right side

### Common Patterns Identified
1. **Search**: Text input with debounced updates
2. **Filters**: Multiple filter types (dropdown, range, checkbox)
3. **Display**: Grid or list layout with items
4. **Selection**: Single-select or multi-select
5. **Loading/Empty states**: Consistent UI patterns

### Modal Requirements (from TASKS.md)

**NewNegotiationModal**:
- Tab 1: Scenario selection (single-select with filters)
- Tab 2: Negotiator selection (multi-select with slots/positions)

**NewTournamentModal**:
- Tab 1: Scenarios (dual-list: available ↔ selected)
- Tab 2: Competitors (dual-list: available ↔ selected)
- Tab 3: Opponents (dual-list: available ↔ selected, with "same as competitors" option)

## Proposed Component Architecture

### 1. ItemSelector Component
**Purpose**: Reusable search/filter/select component for single-select or multi-select scenarios

**Props**:
- `items` (Array): Items to display
- `loading` (Boolean): Loading state
- `searchPlaceholder` (String): Search input placeholder
- `mode` ('single' | 'multi' | 'grid' | 'list'): Display and selection mode
- `filters` (Array): Dynamic filter configuration
- `selectedItems` (Array): Currently selected items (for multi-select)
- `itemKey` (String): Unique key property name
- `displayTemplate` (String | Slot): How to render each item

**Features**:
- Built-in search with debounce
- Dynamic filter rendering based on configuration
- Grid or list layout
- Single or multi-selection
- Emit: `select`, `unselect`, `update:selectedItems`

**Filter Configuration Format**:
```javascript
[
  { type: 'dropdown', label: 'Source', key: 'source', options: [...] },
  { type: 'range', label: 'Outcomes', key: 'outcomes', min: 0, max: 1000 },
  { type: 'checkbox', label: 'Available Only', key: 'availableOnly' }
]
```

**Slots**:
- `item` - Custom item rendering
- `empty` - Custom empty state
- `header-actions` - Additional header buttons

### 2. DualListSelector Component
**Purpose**: Two-panel selector with available ↔ selected transfer (for tournaments)

**Structure**:
```
┌─────────────────────────────────────────────────┐
│ Available Items          │  Selected Items      │
│ [Search]                 │  [Count Badge]       │
│ [Filters]                │                      │
│ [ ] Item 1               │  ☑ Item A  [Remove]  │
│ [ ] Item 2               │  ☑ Item B  [Remove]  │
│ [ ] Item 3               │  [Clear All]         │
│ [Add All Filtered]       │                      │
└─────────────────────────────────────────────────┘
         ↑                           ↑
    Uses ItemSelector          Simple list
```

**Props**:
- `availableItems` (Array): Items that can be selected
- `selectedItems` (Array): Currently selected items
- `filters` (Array): Filter configuration
- `allowDuplicates` (Boolean): Can same item be selected multiple times
- `minSelected` (Number): Minimum selection required

**Features**:
- Left panel: Full ItemSelector with filters
- Right panel: Simple list of selected items with remove buttons
- Transfer buttons: Add all filtered, Remove all
- Validation: Minimum/maximum selections

### 3. RefactoringScenariosView & NegotiatorsView

**Before**: Monolithic view with embedded filters and list
**After**: Composition of reusable components

```vue
<template>
  <div class="scenarios-view">
    <ItemSelector
      :items="scenarios"
      :loading="loading"
      mode="grid"
      :filters="scenarioFilters"
      @select="selectScenario"
    >
      <template #item="{ item }">
        <ScenarioCard :scenario="item" />
      </template>
    </ItemSelector>
    
    <ScenarioDetails :scenario="selectedScenario" />
  </div>
</template>
```

### 4. Update Modals

**NewNegotiationModal - Tab 1 (Scenarios)**:
```vue
<ItemSelector
  :items="scenarios"
  mode="grid"
  :filters="scenarioFilters"
  @select="selectScenario"
/>
```

**NewTournamentModal - Tab 1 (Scenarios)**:
```vue
<DualListSelector
  :availableItems="scenarios"
  :selectedItems="selectedScenarios"
  :filters="scenarioFilters"
  @update:selectedItems="selectedScenarios = $event"
/>
```

## Benefits

### ✅ Code Reusability
- Single implementation of search/filter/select logic
- Used in 2 explorer views + 2 modal dialogs = 4 places
- Reduces duplication from ~400 lines × 2 = 800 lines to ~300 lines (shared)

### ✅ Consistency
- Identical UX across all selection interfaces
- Same filter behavior everywhere
- Easier to maintain and update

### ✅ Maintainability
- Fix bugs once, applies everywhere
- Add new filter types in one place
- Easier to test (isolated components)

### ✅ Flexibility
- Dynamic filter configuration
- Easy to add new item types (e.g., virtual negotiators, saved configs)
- Slot-based customization for special cases

## Implementation Steps

### Phase 1: Create Base Components
1. ✅ Analyze current patterns (DONE)
2. Create `ItemSelector.vue` component
3. Create `DualListSelector.vue` component
4. Create shared filter configuration helpers

### Phase 2: Refactor Explorer Views
5. Update `ScenariosView.vue` to use ItemSelector
6. Update `NegotiatorsView.vue` to use ItemSelector
7. Test explorer views thoroughly

### Phase 3: Update Modals
8. Update `NewNegotiationModal.vue` Tab 1 to use ItemSelector
9. Update `NewNegotiationModal.vue` Tab 2 to use ItemSelector (multi-mode)
10. Update `NewTournamentModal.vue` Tab 1 to use DualListSelector
11. Update `NewTournamentModal.vue` Tab 2 to use DualListSelector
12. Update `NewTournamentModal.vue` Tab 3 to use DualListSelector

### Phase 4: Testing & Refinement
13. End-to-end testing of all selection flows
14. Performance testing with large datasets
15. Accessibility testing (keyboard navigation, screen readers)
16. Style refinement to match Alpine exactly

## Risks & Mitigation

### Risk: Over-abstraction
**Mitigation**: Keep components simple, use slots for customization, allow escape hatches

### Risk: Performance with large lists
**Mitigation**: Virtual scrolling for 500+ items, memoization, lazy loading

### Risk: Breaking existing functionality
**Mitigation**: Incremental refactoring, keep old code until new is tested, feature flags

## Decision: Proceed?

**Recommendation**: ✅ **YES - Proceed with refactoring**

**Rationale**:
1. Clear duplication exists (search/filter/list in 4 places)
2. Modals need this functionality anyway (per TASKS.md)
3. Benefits outweigh complexity
4. Can be done incrementally without breaking existing code
5. Improves long-term maintainability significantly

**Estimated Effort**: 
- ItemSelector: 4-6 hours
- DualListSelector: 3-4 hours  
- Refactoring views: 2-3 hours
- Updating modals: 4-6 hours
- Testing: 3-4 hours
- **Total**: ~16-23 hours (2-3 days)

## Next Actions
1. Wait for user testing feedback on current panel system
2. If approved, create ItemSelector component first
3. Test in one view (ScenariosView) before rolling out
4. Iterate based on feedback
