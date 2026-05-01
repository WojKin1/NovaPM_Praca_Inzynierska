from .models import WBSElement


def generate_next_code(project, parent=None):
    if parent is None:
        roots = WBSElement.objects.filter(project=project, parent=None)
        max_num = 0
        for el in roots:
            try:
                max_num = max(max_num, int(el.code))
            except (ValueError, TypeError):
                pass
        return str(max_num + 1)
    else:
        children = WBSElement.objects.filter(project=project, parent=parent)
        max_num = 0
        prefix = parent.code + '.'
        for el in children:
            if el.code.startswith(prefix):
                last = el.code[len(prefix):].split('.')[0]
                try:
                    max_num = max(max_num, int(last))
                except (ValueError, TypeError):
                    pass
        return f'{parent.code}.{max_num + 1}'


def _recalculate_children(parent, parent_code):
    children = list(parent.children.order_by('order'))
    for i, child in enumerate(children, 1):
        child.code = f'{parent_code}.{i}'
        child.save(update_fields=['code'])
        _recalculate_children(child, child.code)


def recalculate_codes(project):
    roots = list(WBSElement.objects.filter(project=project, parent=None).order_by('order'))
    for i, root in enumerate(roots, 1):
        root.code = str(i)
        root.save(update_fields=['code'])
        _recalculate_children(root, root.code)


def get_tree(project):
    elements = list(WBSElement.objects.filter(project=project).order_by('order'))
    elem_dict = {e.id: e for e in elements}
    for e in elements:
        e.children_list = []
    roots = []
    for e in elements:
        if e.parent_id is None:
            roots.append(e)
        else:
            parent = elem_dict.get(e.parent_id)
            if parent is not None:
                parent.children_list.append(e)
    return roots


def would_create_cycle(element, new_parent):
    """Returns True if setting element.parent = new_parent would create a cycle."""
    if new_parent.id == element.id:
        return True
    cursor = new_parent
    while cursor.parent_id is not None:
        if cursor.parent_id == element.id:
            return True
        cursor = cursor.parent
    return False
