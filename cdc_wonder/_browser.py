# Copyright (c) 2026 Theodore Caputi
# SPDX-License-Identifier: MIT

"""Playwright browser automation for CDC WONDER form submission."""

from __future__ import annotations

import platform
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # playwright types imported lazily


def _user_agent() -> str:
    """Build a Chrome-like user-agent string for the current OS."""
    system = platform.system()
    if system == "Windows":
        os_token = "Windows NT 10.0; Win64; x64"
    elif system == "Darwin":
        os_token = "Macintosh; Intel Mac OS X 10_15_7"
    else:
        os_token = "X11; Linux x86_64"
    return (
        f"Mozilla/5.0 ({os_token}) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

# How long to wait after a search-mode navigation (seconds)
_NAV_SLEEP = 2.5


def _accept_disclaimer(page) -> None:
    try:
        agree = page.locator("input[value='I Agree']")
        if agree.count() > 0 and agree.first.is_visible():
            agree.first.click()
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1.5)
    except Exception:
        pass


def _select_safe(page, field: str, values: list[str]) -> None:
    """Select option(s) in a <select> or <select multiple>.

    Tries three strategies in order:
    1. Playwright select_option by value (fastest, works when values match).
    2. Playwright select_option by label (for fields like V_D77.V5 where
       option values are short codes but we pass the display labels).
    3. JavaScript fallback matching both value and trimmed textContent.
    """
    # Strategy 1: match by value
    try:
        page.select_option(f"select[name='{field}']", values)
        time.sleep(0.1)
        return
    except Exception:
        pass

    # Strategy 2: match by label (display text)
    try:
        label_opts = [{"label": v} for v in values]
        page.select_option(f"select[name='{field}']", label_opts)
        time.sleep(0.1)
        return
    except Exception:
        pass

    # Strategy 3: JS fallback — match against both value and textContent
    page.evaluate(f"""() => {{
        const sel = document.querySelector('select[name="{field}"]');
        if (!sel) return;
        const vals = {values!r};
        for (const opt of sel.options) {{
            opt.selected = vals.includes(opt.value) ||
                           vals.includes((opt.textContent || '').trim());
        }}
        sel.dispatchEvent(new Event('change', {{bubbles: true}}));
    }}""")
    time.sleep(0.1)


def _activate_search_mode(page, var_stem: str, codes: list[str]) -> str:
    """Activate ICD-10 finder and set codes.

    Handles two CDC WONDER form layouts:

    * Browse available (e.g. D157 / mcd_expanded):
        Browse → select chapter ranges → Open Fully → select individual codes
        in F_{var_stem} → set finder-stage='search'

    * No Browse (e.g. D77 / mcd):
        Click Search button → navigate to search-mode form →
        inject codes into V_{var_stem} textarea → set finder-stage='search'
        (stage='codeset' with individual codes is ignored by the D77 server)

    Returns the finder-stage value after activation.
    """
    stage_name      = f"finder-stage-{var_stem}"
    browse_name     = f"finder-action-{var_stem}-Browse"
    open_fully_name = f"finder-action-{var_stem}-Open Fully"

    has_browse = page.evaluate(
        f'() => !!document.querySelector(\'input[name="{browse_name}"]\')'
    )

    if has_browse:
        # ── Browse → Open Fully → select individual codes → stage='search' ────
        with page.expect_navigation(wait_until="domcontentloaded", timeout=30_000):
            page.locator(f'input[name="{browse_name}"]').click()
        time.sleep(_NAV_SLEEP)

        _select_finder_ranges_for_codes(page, var_stem, codes)
        time.sleep(0.5)

        has_open_fully = page.evaluate(
            f'() => !!document.querySelector(\'input[name="{open_fully_name}"]\')'
        )
        if has_open_fully:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=30_000):
                page.locator(f'input[name="{open_fully_name}"]').click()
            time.sleep(_NAV_SLEEP)

        _select_finder_individual_codes(page, var_stem, codes)
        time.sleep(0.5)

        # After Browse+OpenFully the codes live in F_{var_stem}; stage='search'
        # signals CDC WONDER to use those selections.
        page.evaluate(f"""() => {{
            const st = document.querySelector('[name="{stage_name}"]');
            if (st) st.value = 'search';
        }}""")
        time.sleep(0.3)

    else:
        # ── No Browse (e.g. D77 / mcd): Search button → textarea injection ───
        # D77 has a Search button (finder-action-D77.V13-Search) instead of Browse.
        # Clicking Search navigates to the search-mode form where V_{var_stem}
        # (a textarea) is exposed.  We inject the codes there and set
        # finder-stage='search'.  stage='codeset' with individual codes does NOT
        # work on D77 — CDC WONDER ignores it and returns all-cause mortality.
        search_name = f"finder-action-{var_stem}-Search"
        has_search = page.evaluate(
            f'() => !!document.querySelector(\'input[name="{search_name}"]\')'
        )

        if has_search:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=30_000):
                page.locator(f'input[name="{search_name}"]').click()
            time.sleep(_NAV_SLEEP)

        # Whether or not Search button existed, inject codes into the textarea.
        # After Search navigation the textarea V_{var_stem} is available.
        code_str = "\n".join(codes)
        page.evaluate(f"""() => {{
            const ta = document.querySelector('textarea[name="V_{var_stem}"]');
            if (ta) ta.value = {code_str!r};
            const st = document.querySelector('[name="{stage_name}"]');
            if (st) st.value = 'search';
        }}""")
        time.sleep(0.3)

    return page.evaluate(f"""() => {{
        const el = document.querySelector('[name="{stage_name}"]');
        return el ? el.value : '?';
    }}""")


def _set_icd10_via_js(page, var_stem: str, codes: list[str]) -> None:
    """Set a text-area ICD-10 filter by injecting finder-stage='search' via JS.

    This avoids a second page navigation and is used after the primary
    search-mode activation for a different variable has reset this field.
    """
    textarea_name = f"V_{var_stem}"
    stage_name    = f"finder-stage-{var_stem}"
    code_str = "\n".join(codes)
    page.evaluate(f"""() => {{
        const ta = document.querySelector('textarea[name="{textarea_name}"]');
        if (ta) ta.value = {code_str!r};
        const st = document.querySelector('[name="{stage_name}"]');
        if (st) st.value = 'search';
    }}""")
    time.sleep(0.1)


def _apply_base_filters(page, ds: dict, group_by: list[str],
                        demographic_filters: dict) -> None:
    """Apply group-by and all demographic/year filters to the current form."""
    # No-grouping value (first option in B_2..B_5)
    no_group = page.evaluate(
        "() => { const s = document.querySelector('select[name=\"B_2\"]'); "
        "return s ? s.options[0].value : '*None*'; }"
    )

    for i, dim in enumerate(group_by[:5], 1):
        page.select_option(f"select[name='B_{i}']", ds["group_by"][dim])
    for i in range(len(group_by) + 1, 6):
        try:
            page.select_option(f"select[name='B_{i}']", no_group)
        except Exception:
            pass

    for key, values in demographic_filters.items():
        field = ds["filters"][key]
        _select_safe(page, field, values)

    time.sleep(0.2)


def _apply_ucd_drug(page, ds: dict, ucd_drug_codes: list[str]) -> None:
    """Set the UCD drug/alcohol classification filter."""
    fld = ds["ucd_drug_fld"]
    page.locator(f"input[name='O_ucd'][value='{fld}']").click()
    time.sleep(0.4)
    drug_select = f"F_{fld}"
    vis = page.evaluate(f"""() => {{
        const el = document.querySelector('select[name="{drug_select}"]');
        return el && window.getComputedStyle(el).display !== 'none';
    }}""")
    if vis:
        page.select_option(f"select[name='{drug_select}']", ucd_drug_codes)
    else:
        page.evaluate(f"""() => {{
            const sel = document.querySelector('select[name="{drug_select}"]');
            if (!sel) return;
            const vals = {ucd_drug_codes!r};
            for (const opt of sel.options) opt.selected = vals.includes(opt.value);
            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
        }}""")
    time.sleep(0.2)


def _apply_ucd_chapter(page, ds: dict, ucd_chapter: list[str]) -> None:
    """Set the UCD ICD chapter filter (chapter-level select, F_D*.V2)."""
    _select_safe(page, ds["ucd_chapter_fld"], ucd_chapter)


def _apply_ucd_113(page, ds: dict, ucd_113_codes: list[str]) -> None:
    """Set UCD filter using the ICD-10 113 Cause List (V_D*.V4, O_ucd=D*.V4)."""
    fld = ds["ucd_113_fld"]  # e.g. "D77.V4"
    page.locator(f"input[name='O_ucd'][value='{fld}']").click()
    time.sleep(0.3)
    _select_safe(page, f"V_{fld}", ucd_113_codes)


def _apply_mcd_drug(page, ds: dict, mcd_drug_codes: list[str]) -> None:
    """Set the MCD drug/alcohol classification filter."""
    fld = ds["mcd_drug_fld"]
    page.locator(f"input[name='O_mcd'][value='{fld}']").click()
    time.sleep(0.4)
    drug_select = f"F_{fld}"
    vis = page.evaluate(f"""() => {{
        const el = document.querySelector('select[name="{drug_select}"]');
        return el && window.getComputedStyle(el).display !== 'none';
    }}""")
    if vis:
        page.select_option(f"select[name='{drug_select}']", mcd_drug_codes)
    else:
        page.evaluate(f"""() => {{
            const sel = document.querySelector('select[name="{drug_select}"]');
            if (!sel) return;
            const vals = {mcd_drug_codes!r};
            for (const opt of sel.options) opt.selected = vals.includes(opt.value);
            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
        }}""")
    time.sleep(0.2)


def _icd_code_to_range_prefix(code: str) -> str:
    """Convert ICD code to range prefix for finding containing ranges.

    e.g., "I21" -> "I2", "T40.2" -> "T4", "C33" -> "C3"
    This helps find ranges like "I20-I25", "T40-T40", "C30-C39"
    """
    # Remove decimal part if present
    base = code.split(".")[0]
    # Return first 3 characters: letter + 2 digits (or first 2 chars if shorter)
    return base[:2] if len(base) >= 2 else base


def _find_containing_ranges(available_ranges: list[str], code: str) -> list[str]:
    """Find which available ICD ranges would contain this code.

    Args:
        available_ranges: List of range strings from the select dropdown (e.g., ["I00-I99", "C00-D48"])
        code: ICD code to find ranges for (e.g., "I21")

    Returns:
        List of range strings from available_ranges that contain the code.
    """
    base = code.split(".")[0]  # "I21.09" -> "I21"

    matching_ranges = []
    for range_str in available_ranges:
        if "-" not in range_str:
            continue

        parts = range_str.split("-")
        if len(parts) != 2:
            continue

        range_start, range_end = parts[0].strip(), parts[1].strip()

        # Check if code falls within range
        # Simple string comparison works for ICD codes since they're ordered
        if range_start <= base <= range_end:
            matching_ranges.append(range_str)

    return matching_ranges


def _select_finder_ranges_for_codes(page, var_stem: str, codes: list[str]) -> list[str]:
    """Select range(s) in the finder SELECT element for the given codes.

    Returns the list of ranges selected.
    """
    # First, get all available ranges from the SELECT dropdown
    select_name = f"F_{var_stem}"
    available_ranges = page.evaluate(f"""() => {{
        const select = document.querySelector('select[name="{select_name}"]');
        if (!select) return [];
        return Array.from(select.options)
            .map(opt => opt.value)
            .filter(v => v !== '*All*');  // Exclude "All" option
    }}""")

    # Find which ranges contain our codes
    ranges_to_select = set()
    for code in codes:
        matching = _find_containing_ranges(available_ranges, code)
        ranges_to_select.update(matching)

    ranges_to_select_list = list(ranges_to_select)

    # Select the ranges in the SELECT element
    if ranges_to_select_list:
        page.select_option(f"select[name='{select_name}']", ranges_to_select_list)
        time.sleep(0.3)

    return ranges_to_select_list


def _select_finder_individual_codes(page, var_stem: str, codes: list[str]) -> int:
    """Select individual codes from the expanded finder tree.

    After clicking "Open Fully", individual codes appear as options in the SELECT.
    This function selects them.

    Returns the number of codes selected.
    """
    codes_set = set(codes)
    codes_list = list(codes_set)

    # The individual codes will be in the same F_* select element after Open Fully
    select_name = f"F_{var_stem}"

    result = page.evaluate(f"""() => {{
        const codesToFind = {codes_list!r};
        const select = document.querySelector('select[name="{select_name}"]');
        if (!select) return {{codesSelected: 0, error: "select not found"}};

        const options = Array.from(select.options);
        const matchedCodes = [];
        const foundCodes = [];

        for (const code of codesToFind) {{
            for (const opt of options) {{
                const optValue = opt.value.trim();
                // Check if option value starts with the code (matches both "I21" and "I21.0" etc)
                if (optValue === code || optValue.startsWith(code + '.') || optValue.startsWith(code + ' ')) {{
                    matchedCodes.push(optValue);
                    foundCodes.push(code);
                }}
            }}
        }}

        return {{
            codesSelected: matchedCodes.length,
            matchedCodes: matchedCodes,
            codesToFind: codesToFind,
            total_options: options.length
        }};
    }}""")

    codes_to_select = result.get("matchedCodes", [])
    if codes_to_select:
        try:
            page.select_option(f"select[name='{select_name}']", codes_to_select)
            time.sleep(0.3)
        except Exception:
            pass  # Might fail if codes aren't exact matches

    return result.get("codesSelected", 0)




def run_query(
    ds: dict,
    group_by: list[str],
    demographic_filters: dict,
    ucd_icd10: list[str] | None,
    ucd_chapter: list[str] | None,
    ucd_drug_codes: list[str] | None,
    ucd_113_codes: list[str] | None,
    mcd_icd10: list[str] | None,
    mcd_drug_codes: list[str] | None,
    show_zeros: bool,
    show_suppressed: bool,
    headless: bool,
    tmp_tsv: str,
    verbose: bool,
) -> None:
    """Execute a CDC WONDER query via Playwright and save the TSV.

    Strategy
    --------
    CDC WONDER's ICD-10 text-area filters (V_D*.V2 for UCD, V_D*.V13 for MCD)
    only take effect when finder-stage='search'. Activating search mode requires
    clicking the corresponding Search button, which causes a full page
    navigation that resets all other form fields.

    Algorithm:
      1. Load page + accept disclaimer.
      2. Apply group-by and demographic/year filters.
      3. Apply any simple (no-navigation) filters: drug codes, chapter selects.
      4. If MCD ICD-10 needed: trigger search-mode navigation on V_D*.V13.
         Re-apply all base + simple filters after navigation.
         Set the MCD ICD-10 codes in the text area.
      5. If UCD ICD-10 needed AND MCD ICD-10 was also done:
         Inject UCD ICD-10 codes via JavaScript (sets textarea + finder-stage
         without a second navigation, avoiding a circular re-reset loop).
         If no MCD ICD-10: trigger a normal search-mode navigation for UCD.
      6. Set export options and submit.
    """
    from playwright.sync_api import sync_playwright

    needs_mcd_nav = bool(mcd_icd10)
    needs_ucd_nav = bool(ucd_icd10)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(user_agent=_user_agent())
        page = ctx.new_page()
        page.set_default_timeout(90_000)

        # ── 1. Load form ──────────────────────────────────────────────────────
        if verbose: print(f"[WONDER] Loading {ds['url']!r}…")
        page.goto(ds["url"], wait_until="domcontentloaded")
        time.sleep(1)
        _accept_disclaimer(page)

        # ── 2. Apply base filters ─────────────────────────────────────────────
        if verbose: print("[WONDER] Setting group-by and demographic filters…")
        _apply_base_filters(page, ds, group_by, demographic_filters)
        if ucd_drug_codes:
            _apply_ucd_drug(page, ds, ucd_drug_codes)
        if ucd_chapter:
            _apply_ucd_chapter(page, ds, ucd_chapter)
        if ucd_113_codes:
            _apply_ucd_113(page, ds, ucd_113_codes)
        if mcd_drug_codes:
            _apply_mcd_drug(page, ds, mcd_drug_codes)

        # ── 3. MCD ICD-10 search mode (navigation) ────────────────────────────
        mcd_fld = ds["mcd_icd_fld"]
        ucd_fld = ds["ucd_icd_fld"]

        if needs_mcd_nav:
            if verbose: print(f"[WONDER] MCD codes (codes={mcd_icd10!r})…")
            # Click O_mcd radio to select MCD ICD-10 mode
            page.evaluate(f"""() => {{
                const r = document.querySelector('input[name="O_mcd"][value="{mcd_fld}"]');
                if (r) r.click();
            }}""")
            time.sleep(0.3)
            # Navigate through the finder widget (Browse or Search depending on form).
            # Any navigation resets other form fields, so re-apply base filters after.
            stage = _activate_search_mode(page, mcd_fld, mcd_icd10)
            if verbose: print(f"[WONDER]   MCD codes set: {mcd_icd10}")

            # Re-apply O_mcd radio (navigation may have reset it)
            page.evaluate(f"""() => {{
                const r = document.querySelector('input[name="O_mcd"][value="{mcd_fld}"]');
                if (r) r.click();
            }}""")
            time.sleep(0.3)

            # Re-apply base filters in case navigation reset them
            _apply_base_filters(page, ds, group_by, demographic_filters)
            if ucd_drug_codes:
                _apply_ucd_drug(page, ds, ucd_drug_codes)
            if ucd_chapter:
                _apply_ucd_chapter(page, ds, ucd_chapter)
            if ucd_113_codes:
                _apply_ucd_113(page, ds, ucd_113_codes)
            if mcd_drug_codes:
                _apply_mcd_drug(page, ds, mcd_drug_codes)

            # UCD ICD-10 with MCD present: inject via JS to avoid a second navigation
            if ucd_icd10:
                if verbose: print(f"[WONDER]   UCD codes (codes={ucd_icd10!r})…")
                page.evaluate(f"""() => {{
                    const r = document.querySelector('input[name="O_ucd"][value="{ucd_fld}"]');
                    if (r) r.click();
                }}""")
                time.sleep(0.3)
                _set_icd10_via_js(page, ucd_fld, ucd_icd10)
                # Re-select MCD radio so it's active on submission
                page.evaluate(f"""() => {{
                    const r = document.querySelector('input[name="O_mcd"][value="{mcd_fld}"]');
                    if (r) r.click();
                }}""")
                time.sleep(0.2)
                if verbose: print(f"[WONDER]   Both UCD and MCD codes now set")

        # ── 4. UCD ICD-10 only (no MCD nav) ──────────
        elif needs_ucd_nav:
            if verbose: print(f"[WONDER] UCD codes via Browse workflow (codes={ucd_icd10!r})…")
            page.evaluate(f"""() => {{
                const r = document.querySelector('input[name="O_ucd"][value="{ucd_fld}"]');
                if (r) r.click();
            }}""")
            time.sleep(0.3)
            # Use full Browse workflow for UCD as well
            stage = _activate_search_mode(page, ucd_fld, ucd_icd10)
            if verbose: print(f"[WONDER]   UCD finder-stage={stage!r}, codes: {ucd_icd10}")

            # Re-apply base filters in case Browse navigation reset them
            _apply_base_filters(page, ds, group_by, demographic_filters)
            if mcd_drug_codes:
                _apply_mcd_drug(page, ds, mcd_drug_codes)

        # ── 5. Set export options and submit ──────────────────────────────────
        if verbose: print("[WONDER] Submitting…")
        page.evaluate(f"""() => {{
            const fmt = document.querySelector('select[name="O_export-format"]');
            if (fmt) fmt.value = 'tsv';
            const z = document.querySelector('input[name="O_show_zeros"]');
            if (z) z.checked = {'true' if show_zeros else 'false'};
            const s = document.querySelector('input[name="O_show_suppressed"]');
            if (s) s.checked = {'true' if show_suppressed else 'false'};
        }}""")
        time.sleep(0.2)
        # Check export checkbox using Playwright click (JS doesn't work for this one)
        export_checkbox = page.locator('input[id="export-option"]')
        if export_checkbox.count() > 0:
            export_checkbox.click()
            time.sleep(0.2)

        try:
            # Submit form and wait for download
            if verbose: print("[WONDER] Clicking submit and waiting for download...")
            with page.expect_download(timeout=120_000) as dl_info:
                page.locator("#submit-button1").click()

            download = dl_info.value
            download.save_as(tmp_tsv)
            if verbose: print(f"[WONDER] Downloaded → {tmp_tsv}")

        except Exception as e:
            # Capture page content to help diagnose why CDC WONDER didn't return a TSV
            try:
                err_text = page.inner_text("body")[:2000]
                print(f"[WONDER] Page content on error:\n{err_text}")
            except Exception:
                pass
            browser.close()
            raise RuntimeError(
                f"CDC WONDER form submission failed: {e}"
            ) from e

        browser.close()
