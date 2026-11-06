"""Split #pos / n count values into separate columns.

PCS Table 3 / 4 layout is:  #pos | / | n

Workbook/PDF sometimes stores the whole fraction in one field (e.g. "0 / 1").
Word correctly has: #pos=0, /=/, n=1 (or Neg=1 on legacy forms).
Always normalize to separate numbers before compare/export.
"""

from __future__ import annotations

import re

# ASCII /, fullwidth ／, fraction slash ⁄
_SLASH = r"[/／⁄]"
_FRACTION_RE = re.compile(rf"^(\d+)\s*{_SLASH}\s*(\d+)$")
_FRACTION_LOOSE_RE = re.compile(rf"(\d+)\s*{_SLASH}\s*(\d+)")


def split_pos_n(pos: str, n: str = "") -> tuple[str, str]:
    """Return (pos, n) with combined fractions split into two numbers.

    Examples:
      ("0 / 1", "")  → ("0", "1")   # workbook combined → Word layout
      ("0/1", "")    → ("0", "1")
      ("0", "1")     → ("0", "1")   # already correct Word layout
      ("0 / 1", "1") → ("0", "1")   # fraction in pos, n already has denominator
      ("0 / 1", "5") → ("0 / 1", "5")  # conflicting — leave alone
    """
    pos_s = " ".join((pos or "").replace("\xa0", " ").split())
    n_s = " ".join((n or "").replace("\xa0", " ").split())
    if n_s == "/":
        n_s = ""

    m = _FRACTION_RE.match(pos_s) or _FRACTION_LOOSE_RE.fullmatch(pos_s)
    if m:
        num, den = m.group(1), m.group(2)
        if not n_s or n_s == den:
            return num, den
        # n disagrees with denominator — keep as-is for the caller to flag
        return pos_s, n_s

    return pos_s, n_s


def is_not_included(pos: str, n: str = "") -> bool:
    """True when #pos=0 and n=0 — tissue type not included in the PCS workbook."""
    p, nn = split_pos_n(pos, n)
    return p == "0" and nn == "0"


def looks_like_pathology_not_comment(text: str) -> bool:
    """True when text is pathology/diagnosis (+ counts), not a Normal Comments note."""
    t = " ".join((text or "").replace("\xa0", " ").split())
    if not t:
        return False
    low = t.lower()
    if re.search(
        r"\b(adenocarcinoma|carcinoma|adenoma|tumou?r|neoplasm|melanoma|"
        r"lymphoma|sarcoma|invasive|ductal|endometrioid|serous|mucinous|"
        r"squamous|metastat)\b",
        low,
    ) and re.search(r"\d+\s*/\s*\d+", t):
        return True
    if re.fullmatch(
        r"(adenocarcinoma|carcinoma|adenoma|tumou?r|neoplasm|normal|"
        r"invasive ductal carcinoma|adenocarcinoma\*?)",
        low,
    ):
        return True
    return False


def looks_like_tissue_descriptor_not_comment(text: str) -> bool:
    """True when text is part of a Tissue name, not a Comments cell.

    Cerebrum, Cerebrum (grey matter), and Cerebrum (white matter) are three
    different tissues. Parentheticals like '(grey matter)' / '(white matter)'
    must never be stored or flagged as Comments.

    Bare 'White matter' (no parentheses) can still be a real localisation
    comment on another tissue (e.g. Cerebellum).
    """
    t = " ".join((text or "").replace("\xa0", " ").split())
    if not t:
        return False
    low = t.lower().strip(" .;,:")
    # Incomplete paren fragments from PDF split: "(grey matter"
    if low.startswith("("):
        return True
    # Closing-paren fragments: "grey matter)" / "white matter tissue)"
    if re.fullmatch(r"(grey|gray|white)\s+matter(\s+tissue)?\)", low):
        return True
    # Full tissue-name qualifier including the word "tissue"
    if re.fullmatch(
        r"\(?\s*(grey|gray|white)\s+matter\s+tissue\s*\)?",
        low,
    ):
        return True
    if re.fullmatch(r".+\s+matter\s+tissue\)?", low):
        return True
    return False


def scrub_comments(comments: str, tissue: str = "") -> str:
    """Clear Comments that are really tissue-name qualifiers or pathology residue."""
    c = " ".join((comments or "").replace("\xa0", " ").split())
    if not c:
        return ""
    if looks_like_pathology_not_comment(c):
        return ""
    if looks_like_tissue_descriptor_not_comment(c):
        return ""
    # Comment duplicates a parenthetical already present in the Tissue name
    t_low = (tissue or "").lower()
    c_low = c.lower().strip("()")
    if t_low and c_low and f"({c_low})" in t_low:
        return ""
    if t_low and c_low and c_low in t_low and re.search(
        r"\(\s*(grey|gray|white)\s+matter", t_low
    ):
        return ""
    return c


def tissue_line_match(line: str, tissue: str) -> re.Match[str] | None:
    """Match tissue as a whole name at the start of a PDF text line.

    'Bladder' must not match inside 'Gallbladder'.
    'Cerebrum' must not match 'Cerebrum (grey matter)' / '(white matter)' —
    those are different tissues.
    """
    t = " ".join((tissue or "").replace("\xa0", " ").split())
    if not t:
        return None
    m = re.match(
        rf"^\s*(?:[*•·\-–—]\s*)?{re.escape(t)}(?![A-Za-z0-9])\s*(.*)$",
        (line or "").strip(),
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    rest = (m.group(1) or "").strip()
    # Short name must not claim a line that continues with a matter parenthetical
    if "(" not in t and re.match(
        r"^\(\s*(grey|gray|white)\s+matter",
        rest,
        flags=re.IGNORECASE,
    ):
        return None
    return m


def longest_tissue_for_line(line: str, tissues: list[str]) -> str | None:
    """Which tissue name (longest wins) owns this PDF text line."""
    best: str | None = None
    best_len = -1
    for tissue in tissues:
        m = tissue_line_match(line, tissue)
        if not m:
            continue
        n = len(" ".join((tissue or "").split()))
        if n > best_len:
            best = tissue
            best_len = n
    return best


def looks_like_combined_fraction(pos: str, n: str = "") -> bool:
    """True when #pos holds both numbers and n is blank (wrong Word layout)."""
    pos_s = " ".join((pos or "").replace("\xa0", " ").split())
    n_s = " ".join((n or "").replace("\xa0", " ").split())
    if n_s and n_s != "/":
        return False
    return bool(_FRACTION_RE.match(pos_s) or _FRACTION_LOOSE_RE.fullmatch(pos_s))


def layout_split_note(pos_raw: str) -> str:
    """Human note telling the author how to fix a combined #pos cell."""
    a, b = split_pos_n(pos_raw, "")
    return (
        f"Layout — #pos has both numbers ({pos_raw.strip()}). "
        f"Put {a} in #pos, / in the / column, and {b} in n."
    )
