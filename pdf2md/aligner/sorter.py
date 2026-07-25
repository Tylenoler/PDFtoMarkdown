"""Reading-order sorter: arrange OCR blocks top-to-bottom, left-to-right."""

from typing import Any


def reading_order_sort(
    blocks: list[dict[str, Any]],
    x_tolerance: float = 50.0,
) -> list[dict[str, Any]]:
    """Sort OCR blocks in reading order.

    Within the same row (Y within *x_tolerance*), sort by X ascending.
    Otherwise sort by Y ascending (top to bottom).

    Parameters
    ----------
    blocks : list[dict]
        OCR layout blocks, each with "bbox" ([x0,y0,x1,y1]) or None.
    x_tolerance : float
        Vertical tolerance in points to consider blocks on the same line.

    Returns
    -------
    list[dict]
        Sorted copy of *blocks*.
    """
    def _row_key(block: dict[str, Any]) -> tuple:
        bbox = block.get("bbox")
        if bbox is None:
            return (0, 0)
        y_center = (bbox[1] + bbox[3]) / 2
        row = round(y_center / x_tolerance)
        x_center = (bbox[0] + bbox[2]) / 2
        return (row, x_center)

    return sorted(blocks, key=_row_key)
