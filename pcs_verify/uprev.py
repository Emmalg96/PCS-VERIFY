"""Helpers for PCS form uprev checks (legacy Pos/Neg → modern #pos/n)."""

from __future__ import annotations

from .form import FormRow, ParsedForm


def _intish(value: str) -> int | None:
    v = (value or "").strip()
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def coerce_legacy_counts(
    rows: list[FormRow],
    *,
    neg_means_negative_count: bool,
) -> list[FormRow]:
    """Normalize legacy Pos/Neg rows for comparison to Form9182 #pos / n.

    - Default (False): Neg column already maps to n (rename-style uprev).
    - If neg_means_negative_count: n = Pos + Neg, #pos = Pos.
    """
    if not neg_means_negative_count:
        return rows
    out: list[FormRow] = []
    for r in rows:
        pos_i = _intish(r.pos)
        neg_i = _intish(r.n)  # Neg was stored in n during parse
        if pos_i is not None and neg_i is not None:
            out.append(
                FormRow(
                    tissue=r.tissue,
                    pathology=r.pathology,
                    pos=str(pos_i),
                    n=str(pos_i + neg_i),
                    comments=r.comments,
                )
            )
        else:
            out.append(r)
    return out


def prepare_form_for_uprev(
    form: ParsedForm,
    *,
    neg_means_negative_count: bool = False,
) -> ParsedForm:
    return ParsedForm(
        normal=coerce_legacy_counts(
            form.normal, neg_means_negative_count=neg_means_negative_count
        ),
        abnormal=coerce_legacy_counts(
            form.abnormal, neg_means_negative_count=neg_means_negative_count
        ),
        file_name=form.file_name,
        warnings=list(form.warnings or []),
        count_format=form.count_format,
    )
