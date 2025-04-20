from typing import List

from anytree import Node


def flatten(node: Node, attr: str = "name") -> List[List]:
    result = []
    for child in node.children:
        if child.is_leaf:
            result.append([getattr(node, attr), getattr(child, attr)])
        else:
            result += [
                [getattr(node, attr)] + subpath for subpath in flatten(child, attr)
            ]
    return result
