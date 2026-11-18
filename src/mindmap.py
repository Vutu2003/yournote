"""Grounded, bounded mind maps with global citation IDs across map/reduce."""

from src.config import settings
from src.learning import _parse_json, _resolve_target
from src.llm import invoke_llm
from src.rag import format_citations, render_prompt
from src.schemas import MindMap, MindMapNode, validate_mindmap_tree


def _ground_tree(payload: object, valid_markers: set[str]) -> MindMapNode:
    if not isinstance(payload, dict) or "root" not in payload:
        raise RuntimeError("Mind map output must contain a root node.")
    root = validate_mindmap_tree(MindMapNode.model_validate(payload["root"]))

    def grounded(node: MindMapNode) -> MindMapNode:
        children = [grounded(child) for child in node.children]
        markers = list(dict.fromkeys(marker for marker in node.source_markers if marker in valid_markers))
        if not markers and children:
            markers = list(dict.fromkeys(marker for child in children for marker in child.source_markers))[:16]
        if not markers:
            raise RuntimeError("Mind map contains an idea without a valid source.")
        return node.model_copy(update={"source_markers": markers, "children": children})

    root = grounded(root)
    if not root.children:
        raise RuntimeError("Mind map must contain at least one branch.")
    return root


def _markers(root: MindMapNode) -> set[str]:
    return set(root.source_markers).union(*(_markers(child) for child in root.children))


def generate_mindmap(document=None, query=None, filters=None, k=None) -> MindMap:
    chunks, scope, target = _resolve_target(document, query, filters, k, settings.generation_retrieval_k)
    if not chunks:
        raise RuntimeError("No chunks available for mind map generation.")
    # Every selected chunk is covered. IDs remain global rather than restarting
    # at S1 in each batch, including through multiple reduction rounds.
    batch_size = settings.mindmap_batch_size
    partials = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        prompt = render_prompt("mindmap.jinja2", chunks=batch, start=start, topic=query)
        valid = {f"S{index}" for index in range(start + 1, start + len(batch) + 1)}
        partials.append(_ground_tree(_parse_json(invoke_llm(prompt)), valid))
    while len(partials) > 1:
        reduced = []
        for start in range(0, len(partials), 8):
            group = partials[start:start + 8]
            if len(group) == 1:
                reduced.append(group[0])
                continue
            prompt = render_prompt("mindmap_reduce.jinja2", trees=[tree.model_dump() for tree in group], topic=query)
            reduced.append(_ground_tree(_parse_json(invoke_llm(prompt)), set().union(*(_markers(tree) for tree in group))))
        partials = reduced
    root = partials[0]
    used = _markers(root)
    return MindMap(scope=scope, target=target, root=root,
                   citations=[citation for citation in format_citations(chunks) if citation.source_marker in used])
