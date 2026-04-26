# Code Quality Audit Report

**Date:** January 17, 2026  
**Codebase:** negmas-app  
**Auditor:** AI Code Review

---

## Executive Summary

This audit identified several code quality issues in the negmas-app codebase, ranging from critical duplicate class definitions to minor organizational concerns. The most pressing issues involve **duplicate class definitions with incompatible structures** that could lead to runtime errors or confusing behavior.

**Issue Breakdown:**
- Critical: 2 issues
- High: 6 issues (including 33 type errors across 7 files)
- Medium: 4 issues
- Low: 2 issues

---

## Critical Issues

### 1. Duplicate `MechanismConfig` Class Definitions

**Severity:** CRITICAL  
**Impact:** Ambiguous imports, potential runtime errors, maintenance confusion

**Locations:**

**A) `models/mechanism.py` (lines 85-95):**
```python
@dataclass
class MechanismConfig:
    mechanism_type: MechanismType = MechanismType.SAO
    deadline: DeadlineConfig = field(default_factory=DeadlineConfig)
    sao_params: SAOParams = field(default_factory=SAOParams)
    tau_params: TAUParams = field(default_factory=TAUParams)
    gb_params: GBParams = field(default_factory=GBParams)
    display: DisplayConfig = field(default_factory=DisplayConfig)
```

**B) `models/negotiation_definition.py` (lines 16-22):**
```python
@dataclass
class MechanismConfig:
    class_name: str = "negmas.sao.SAOMechanism"
    params: dict[str, Any] = field(default_factory=dict)
    name: str | None = None
```

**Problem:** These two classes share the same name but have completely different fields. The one in `mechanism.py` is used for UI configuration, while the one in `negotiation_definition.py` is for serialization/definition. This causes:
- Import confusion (which one to use?)
- IDE autocomplete issues
- Potential bugs if wrong class is imported

**Recommended Fix:**
- Rename `models/negotiation_definition.py::MechanismConfig` to `MechanismDefinition`
- Update all references in `DefinitionService` and related code

---

### 2. Duplicate `NegotiatorConfig` Class Definitions

**Severity:** CRITICAL  
**Impact:** Same as above - import ambiguity and potential bugs

**Locations:**

**A) `models/negotiator.py` (lines 35-40):**
```python
@dataclass
class NegotiatorConfig:
    type_name: str
    name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
```

**B) `models/negotiation_definition.py` (lines 25-30):**
```python
@dataclass
class NegotiatorConfig:
    type_name: str
    name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    ufun_index: int = 0
```

**Problem:** These are nearly identical but the one in `negotiation_definition.py` has an additional `ufun_index` field. This subtle difference can cause hard-to-debug issues.

**Recommended Fix:**
- Keep one canonical `NegotiatorConfig` in `models/negotiator.py`
- Add `ufun_index: int = 0` field to it
- Remove duplicate from `models/negotiation_definition.py`
- Or rename the definition version to `NegotiatorDefinition`

---

## High Priority Issues

### 3. Classes Not Exported from `models/__init__.py`

**Severity:** HIGH  
**Impact:** Inconsistent import patterns, some classes require deep imports

**File:** `models/__init__.py`

**Missing Exports:**

| Class | Defined In | Used In |
|-------|-----------|---------|
| `VirtualMechanism` | `models/mechanism.py` | `services/virtual_mechanism_service.py` |
| `VirtualNegotiator` | `models/negotiator.py` | `services/virtual_negotiator_service.py` |
| `PerformanceSettings` | `models/settings.py` | `services/settings_service.py` |
| `TournamentPreset` | `models/settings.py` | `routers/settings.py` |

**Missing Function Export:**

| Function | Defined In | Purpose |
|----------|-----------|---------|
| `compact_layout()` | `models/session.py` | Utility function for layout compaction |

**Recommended Fix:**
Add to `models/__init__.py`:
```python
from .mechanism import VirtualMechanism
from .negotiator import VirtualNegotiator
from .settings import PerformanceSettings, TournamentPreset
from .session import compact_layout
```

---

### 4. Pyright Type Errors (33 errors across 7 files)

**Severity:** HIGH  
**Impact:** Type safety violations, potential runtime errors, IDE warnings

#### 4.1 `services/scenario_loader.py` (9 errors)

| Line | Error |
|------|-------|
| 524 | `"ScenarioDefinition"` is not defined |
| 335 | Cannot access attribute `"load"` for class `"object"` |
| 612 | Expected 1 positional argument |
| 626 | Argument of type `"list[IdentityFun]"` cannot be assigned to parameter `"values"` of type `"dict[str, SingleIssueFun] \| tuple[SingleIssueFun, ...] \| list[SingleIssueFun]"` |
| 648 | Object of type `"object"` is not callable |
| 661 | `"exists"` is not a known attribute of `"None"` |
| 662 | `"parent"` is not a known attribute of `"None"` |
| 662 | `"name"` is not a known attribute of `"None"` |

**Root Cause:** Missing import for `ScenarioDefinition`, improper type narrowing for optional values, and `IdentityFun` vs `SingleIssueFun` type mismatch.

#### 4.2 `services/negotiator_factory.py` (5 errors)

| Line | Error |
|------|-------|
| 308 | Cannot access attribute `"keys"` for class `"object"` |
| 309 | Cannot access attribute `"get"` for class `"object"` |
| 779 | Type `"BOANegotiator"` is not assignable to return type `"SAONegotiator"` |
| 894 | Type `"MAPNegotiator"` is not assignable to return type `"SAONegotiator"` |
| 1128 | Type `"GBNegotiator[Unknown, Unknown]"` is not assignable to return type `"SAONegotiator"` |

**Root Cause:** Return type annotations are too narrow. Functions return various negotiator subclasses but declare `SAONegotiator` return type.

**Recommended Fix:** Change return types to `Negotiator` or use `Union` types:
```python
def create_boa_negotiator(...) -> BOANegotiator | SAONegotiator:
def create_map_negotiator(...) -> MAPNegotiator | SAONegotiator:
def create_gb_negotiator(...) -> GBNegotiator | SAONegotiator:
```

#### 4.3 `services/session_manager.py` (2 errors)

| Line | Error |
|------|-------|
| 334 | Cannot assign to attribute `"error_message"` for class `"NegotiationSession"` - attribute is unknown |
| 409 | Argument of type `"Mechanism[...]"` cannot be assigned to parameter `"mechanism"` of type `"SAOMechanism"` |

**Root Cause:** 
- `NegotiationSession` dataclass is missing `error_message` field
- Function parameter typed too narrowly as `SAOMechanism` instead of generic `Mechanism`

**Recommended Fix:** Add `error_message: str | None = None` to `NegotiationSession` dataclass in `models/session.py`

#### 4.4 `services/outcome_analysis.py` (5 errors)

| Line | Error |
|------|-------|
| 155 | Object of type `"object"` is not callable |
| 179 | Object of type `"object"` is not callable |
| 195 | Object of type `"object"` is not callable |
| 211 | Object of type `"object"` is not callable |
| 227 | Object of type `"object"` is not callable |

**Root Cause:** Variables typed as `object` are being called as functions. Likely missing type annotations or improper type narrowing.

#### 4.5 `services/module_inspector.py` (2 errors)

| Line | Error |
|------|-------|
| 329 | Argument of type `"Any \| object"` cannot be assigned to parameter `"class_or_tuple"` of type `"_ClassInfo"` in function `isinstance` |
| 404 | Cannot access attribute `"load"` for class `"object"` |

**Root Cause:** Using `isinstance()` with a variable that could be `object` type instead of a proper class.

#### 4.6 `services/negotiation_loader.py` (1 error)

| Line | Error |
|------|-------|
| 235 | Cannot access attribute `"keys"` for class `"tuple[Issue, ...]"` |

**Root Cause:** Code assumes `issues` is a dict-like object but it's typed as `tuple[Issue, ...]`.

**Recommended Fix:** Check the actual type at runtime or update type annotation.

#### 4.7 `services/tournament_storage.py` (9 errors)

| Line | Error |
|------|-------|
| 363 | Operator `"+"` not supported for types `"Hashable"` and `"Literal[1]"` |
| 364 | Argument of type `"Unknown \| None"` cannot be assigned to parameter `"x"` of type `"ConvertibleToFloat"` |
| 364 | Invalid conditional operand of type `"bool \| NDArray[bool_] \| NDFrame"` |
| 1207 | Argument of type `"int"` cannot be assigned to parameter `"value"` of type `"bool"` |
| 1211 | Argument of type `"int"` cannot be assigned to parameter `"value"` of type `"bool"` |
| 1213 | Argument of type `"int"` cannot be assigned to parameter `"value"` of type `"bool"` |
| 1246 | Cannot access attribute `"load"` for class `"object"` |
| 1486 | Cannot access attribute `"load"` for class `"object"` |

**Root Cause:** 
- Pandas DataFrame operations with improper type handling
- Using `int` where `bool` is expected (likely intentional 0/1 values)
- Dynamic loading with `object` typed variables

**Recommended Fix for int/bool issues:** Use explicit boolean values:
```python
# Instead of: df['column'] = 1
df['column'] = True
```

---

## Medium Priority Issues

### 5. Duplicate `PANEL_TYPES` Constant

**Severity:** MEDIUM  
**Impact:** Maintenance burden, risk of divergence

**Locations:**
- `models/session.py` line 140
- `models/settings.py` line 109

**Recommended Fix:**
- Keep `PANEL_TYPES` in one location (suggest `models/session.py` since it's layout-related)
- Import it in `models/settings.py` from session

---

### 6. Duplicate/Conflicting `LayoutConfig` Classes

**Severity:** MEDIUM  
**Impact:** Confusion about which to use, potential bugs

**Locations:**

**A) `models/session.py`:**
```python
@dataclass
class LayoutConfig:
    zones: dict[str, ZoneConfig]  # Different structure
    ...
```

**B) `models/settings.py`:**
```python
@dataclass
class LayoutConfig:
    zones: dict[str, ZoneConfig]
    zone_sizes: ZoneSizes
    ...
```

**Problem:** These may have subtle structural differences that cause issues when one is expected but the other is used.

**Recommended Fix:**
- Consolidate into single `LayoutConfig` class
- Keep in `models/settings.py` (settings-related)
- Import in `models/session.py`

---

### 7. Layout-Related Classes Split Across Files

**Severity:** MEDIUM  
**Impact:** Unclear where to find layout types, scattered definitions

**Issue:** Layout-related classes are split between:
- `models/session.py`: `LayoutConfig`, `PanelState`, `ZoneConfig`
- `models/settings.py`: `ZoneConfig`, `ZoneSizes`, `LayoutConfig`, `LayoutState`

**Recommended Fix:**
- Create `models/layout.py` to consolidate all layout-related types
- Move: `ZoneConfig`, `ZoneSizes`, `LayoutConfig`, `LayoutState`, `PanelState`, `compact_layout()`
- Update imports in both `session.py` and `settings.py`

---

### 8. Potential Circular Import Risk

**Severity:** MEDIUM  
**Impact:** Import errors at runtime

**Location:** `services/scenario_loader.py` line 545

```python
from ..models.scenario import ScenarioDefinition
```

**Note:** This import pattern (`..models.scenario`) from a services file importing models is fine. However, if `models/scenario.py` ever imports from services, it would create a circular import.

**Recommended Action:** 
- Document the import direction rule: models should never import from services
- Consider adding a pre-commit check for circular imports

---

## Low Priority Issues

### 9. Unused Imports (To Verify)

**Severity:** LOW  
**Impact:** Minor code cleanliness

**Action:** Run the following to identify unused imports:
```bash
# Using ruff
ruff check --select F401 negmas_app/

# Or using pyflakes
pyflakes negmas_app/
```

**Recommended Fix:**
- Remove any confirmed unused imports
- Configure pre-commit hook to catch future unused imports

---

### 10. Inconsistent Module `__all__` Exports

**Severity:** LOW  
**Impact:** Unclear public API surface

**Issue:** Some modules define `__all__`, others don't. This makes it unclear what the public API is.

**Affected Files:**
- `models/__init__.py` - has exports but no `__all__`
- `services/__init__.py` - has exports but no `__all__`
- `routers/__init__.py` - has exports but no `__all__`

**Recommended Fix:**
- Add `__all__` lists to all `__init__.py` files
- This documents the public API and helps tools like linters

---

## Recommended Actions Summary

### Immediate (This Week)
1. Rename `MechanismConfig` in `negotiation_definition.py` to `MechanismDefinition`
2. Consolidate `NegotiatorConfig` to single definition with `ufun_index` field
3. Add missing exports to `models/__init__.py`
4. Fix critical type errors:
   - Add `error_message` field to `NegotiationSession`
   - Add missing `ScenarioDefinition` import in `scenario_loader.py`
   - Fix return type annotations in `negotiator_factory.py`

### Short-term (This Month)
5. Consolidate `PANEL_TYPES` to single location
6. Create `models/layout.py` for layout-related types
7. Consolidate `LayoutConfig` definitions
8. Fix remaining type errors (proper type narrowing, None checks)

### Long-term
9. Add `__all__` exports to all `__init__.py` files
10. Set up pre-commit hooks for:
    - Unused import detection
    - Circular import detection
    - Type checking (pyright)
11. Clean up any unused imports found

---

## Appendix: File Reference

### Models Directory Structure
```
models/
├── __init__.py           # Exports (needs update)
├── mechanism.py          # MechanismConfig, VirtualMechanism, MechanismType, etc.
├── negotiation_definition.py  # MechanismConfig (DUPLICATE), NegotiatorConfig (DUPLICATE)
├── negotiator.py         # NegotiatorConfig, VirtualNegotiator, BOANegotiatorConfig
├── scenario.py           # ScenarioInfo, ScenarioStatsInfo
├── session.py            # NegotiationSession, LayoutConfig, PANEL_TYPES
├── settings.py           # AppSettings, LayoutConfig, PANEL_TYPES (DUPLICATES)
└── tournament.py         # TournamentConfig, TournamentSession
```

### Import Dependency Graph (Simplified)
```
routers/* 
    ↓
services/*
    ↓
models/*
```
**Rule:** Arrows point downward only. No upward imports allowed.
