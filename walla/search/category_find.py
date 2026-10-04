"""Find leaf/root category ids by name tokens (pure)."""

from __future__ import annotations

from dataclasses import dataclass

from walla.models.profile import Category

__all__ = (
    "CategoryHit",
    "find_categories",
    "flatten_categories",
    "resolve_root_id",
)


@dataclass(frozen=True)
class CategoryHit:
    leaf_id: str
    root_id: str
    path: str
    name: str
    is_leaf: bool


def flatten_categories(roots: list[Category]) -> list[CategoryHit]:
    """Walk the tree; every node becomes a hit with its root id."""
    out: list[CategoryHit] = []

    def walk(nodes: list[Category], root_id: int, parts: tuple[str, ...]) -> None:
        for node in nodes:
            path_parts = parts + (node.name,)
            kids = list(node.subcategories)
            out.append(
                CategoryHit(
                    leaf_id=str(node.id),
                    root_id=str(root_id),
                    path=" / ".join(path_parts),
                    name=node.name,
                    is_leaf=not kids,
                )
            )
            if kids:
                walk(kids, root_id, path_parts)

    for root in roots:
        walk([root], root.id, ())
    return out


def find_categories(roots: list[Category], query: str) -> list[CategoryHit]:
    """Rank hits whose path contains every query token (space or /)."""
    tokens = [t for t in query.lower().replace("/", " ").split() if t]
    if not tokens:
        raise ValueError("category find query is empty")
    scored: list[tuple[int, CategoryHit]] = []
    for hit in flatten_categories(roots):
        blob = hit.path.lower()
        if not all(tok in blob for tok in tokens):
            continue
        score = 0
        if hit.is_leaf:
            score += 20
        name_l = hit.name.lower()
        joined = " ".join(tokens)
        if name_l == joined or _stem(name_l) == _stem(tokens[-1]):
            score += 50
        elif tokens[-1] == name_l or _stem(tokens[-1]) == _stem(name_l):
            score += 40
        elif name_l.startswith(tokens[-1]) or tokens[-1].startswith(_stem(name_l)):
            score += 25
        score += sum(6 for tok in tokens if tok in name_l)
        # Prefer the named leaf over a shallow cousin that only contains the token.
        if any(_stem(part) == _stem(tokens[-1]) for part in blob.split(" / ")):
            score += 15
        scored.append((score, hit))
    scored.sort(key=lambda row: (-row[0], len(row[1].path), row[1].path.lower()))
    return [hit for _, hit in scored]


def _stem(word: str) -> str:
    w = word.lower().strip()
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and len(w) > 3:
        return w[:-1]
    return w


def resolve_root_id(roots: list[Category], leaf_id: str) -> str:
    """Return the root category id that owns leaf_id."""
    needle = str(leaf_id).strip()
    if not needle:
        raise ValueError("leaf category id is empty")
    for hit in flatten_categories(roots):
        if hit.leaf_id == needle:
            return hit.root_id
    raise ValueError(f"unknown category leaf id: {needle}")
