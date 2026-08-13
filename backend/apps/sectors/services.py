def build_sector_tree(sectors):
    nodes = {
        sector.pk: {
            "id": sector.pk,
            "unit": sector.unit_id,
            "unit_name": sector.unit.name if sector.unit else None,
            "unit_acronym": sector.unit.acronym if sector.unit else None,
            "name": sector.name,
            "code": sector.code,
            "parent": sector.parent_id,
            "manager": sector.manager_id,
            "manager_name": sector.manager.full_name if sector.manager else None,
            "active": sector.active,
            "children": [],
        }
        for sector in sectors
    }
    roots = []
    for sector_id, node in nodes.items():
        parent = nodes.get(node["parent"])
        if parent:
            parent["children"].append(node)
        else:
            roots.append(node)
    return roots
