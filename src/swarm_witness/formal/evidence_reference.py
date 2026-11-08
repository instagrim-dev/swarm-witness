"""Separately encoded set-rule reference for the evidence binding.

This module does not import the production verdict, the adapter, or
``conclusion_classes``. Support and refutation are the nonempty subset
rules on a finite mask. Empty compatibility and failed verification stay
unresolved. Soundness still assumes the actual world was not removed from
the compatible set.
"""

from __future__ import annotations


def reference_verdict(
    property_mask: int,
    evidence_mask: int,
    *,
    verified: bool,
    width: int,
) -> str:
    """Return supported, refuted, or unresolved for one finite mask pair.

    ``width`` is the declared universe size. Masks outside that width are
    rejected. A false verification flag and a zero evidence mask are both
    unresolved, including the vacuous case of an empty compatible set.
    """
    if not isinstance(width, int) or width < 1 or width > 8:
        raise ValueError(f"unsupported finite width: {width!r}")
    full = (1 << width) - 1
    if (
        not isinstance(property_mask, int)
        or not isinstance(evidence_mask, int)
        or property_mask < 0
        or evidence_mask < 0
        or property_mask > full
        or evidence_mask > full
    ):
        raise ValueError("mask is outside the declared finite universe")
    if verified is not True or evidence_mask == 0:
        return "unresolved"
    outside = (~property_mask) & full
    if evidence_mask & outside == 0:
        return "supported"
    if evidence_mask & property_mask == 0:
        return "refuted"
    return "unresolved"
