"""Conservative, detached public context projection for the virtual operator."""

from .model_operator_boundary import _CONTEXT_BYTES, _context, _snapshot

__all__ = ["project_operator_context"]

_DEVICE_REFERENCES = frozenset(("device_id", "source_id", "input_source_id", "reference_source_id"))


def _unresolved_reference(value, known):
    if type(value) is dict:
        for key, item in value.items():
            if key in _DEVICE_REFERENCES and (type(item) is not str or item not in known):
                return True
            if _unresolved_reference(item, known):
                return True
    elif type(value) is list:
        return any(_unresolved_reference(item, known) for item in value)
    return False


def _references(value, known):
    """Find explicit values naming topology nodes without interpreting unknown IDs."""
    if type(value) is str:
        return {value} if value in known else set()
    if type(value) is list:
        found = set()
        for item in value:
            found.update(_references(item, known))
        return found
    if type(value) is dict:
        found = set()
        for item in value.values():
            found.update(_references(item, known))
        return found
    return set()


def _compact(value):
    topology = value["topology"]
    if set(topology) != {"devices", "connections"} or type(topology["connections"]) is not list:
        return None
    nodes, profiles = topology["devices"], value["catalog"]["profiles"]
    observations = value["observations"]["devices"]
    actions = value["role_actions"]
    by_profile = {}
    for profile in profiles:
        identity, role, ports = profile.get("profile_id"), profile.get("role"), profile.get("ports")
        if (type(identity) is not str or not identity or identity in by_profile
                or type(role) is not str or not role or role not in actions
                or type(ports) is not dict or set(ports) != {"inputs", "outputs"}
                or type(ports["inputs"]) is not dict or type(ports["outputs"]) is not dict):
            return None
        by_profile[identity] = profile
    by_node = {}
    for node in nodes:
        if type(node) is not dict or set(node) != {"id", "profile_id"}:
            return None
        identity, profile_id = node["id"], node["profile_id"]
        if (type(identity) is not str or not identity or identity in by_node
                or type(profile_id) is not str or profile_id not in by_profile):
            return None
        by_node[identity] = node
    if set(observations) != set(by_node):
        return None
    for identity, node in by_node.items():
        observed = observations[identity]
        if (type(observed) is not dict or observed.get("device_id") != identity
                or observed.get("profile_id") != node["profile_id"]
                or observed.get("role") != by_profile[node["profile_id"]]["role"]):
            return None
    known = set(by_node)
    goal = value["goal"]
    selected = {goal["dut_id"], goal["sensor_id"]}
    if not selected <= known:
        return None
    receipt = value["last_receipt"]
    if receipt is not None:
        if _unresolved_reference(receipt, known):
            return None
        if any(key in receipt for key in ("device_id", "profile_id", "role")):
            if type(receipt.get("device_id")) is not str or receipt["device_id"] not in known:
                return None
            node = by_node[receipt["device_id"]]
            if (receipt.get("profile_id") != node["profile_id"]
                    or receipt.get("role") != by_profile[node["profile_id"]]["role"]):
                return None
            selected.add(receipt["device_id"])
        elif (set(receipt) != {"hardware_verified", "setup_revision", "status", "synthetic", "tick", "values"}
              or type(receipt["values"]) is not dict or set(receipt["values"]) != {"advanced_ticks"}
              or type(receipt["values"]["advanced_ticks"]) is not int):
            return None
        selected.update(_references(receipt, known))
    graph = {identity: set() for identity in known}
    successors = {identity: set() for identity in known}
    indegree = dict.fromkeys(known, 0)
    targets = set()
    for edge in topology["connections"]:
        if type(edge) is not dict or set(edge) != {"source", "target", "kind"}:
            return None
        kind = edge["kind"]
        if type(kind) is not str or not kind:
            return None
        names = []
        for direction, ports_name in (("source", "outputs"), ("target", "inputs")):
            endpoint = edge[direction]
            if type(endpoint) is not dict or set(endpoint) != {"device_id", "port"}:
                return None
            identity, port = endpoint["device_id"], endpoint["port"]
            if (type(identity) is not str or identity not in by_node
                    or type(port) is not str or not port):
                return None
            profile = by_profile[by_node[identity]["profile_id"]]
            if profile["ports"][ports_name].get(port) != kind:
                return None
            names.append(identity)
        target = (edge["target"]["device_id"], edge["target"]["port"])
        if target in targets:
            return None
        targets.add(target)
        graph[names[0]].add(names[1])
        graph[names[1]].add(names[0])
        if names[1] not in successors[names[0]]:
            successors[names[0]].add(names[1])
            indegree[names[1]] += 1
    ready = [identity for identity, degree in indegree.items() if degree == 0]
    ordered = 0
    while ready:
        ordered += 1
        for neighbor in successors[ready.pop()]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                ready.append(neighbor)
    if ordered != len(known):
        return None
    # Close over every declared connection kind, then over references naming
    # known topology nodes in retained payloads.
    while True:
        before = len(selected)
        pending = list(selected)
        while pending:
            for neighbor in graph[pending.pop()]:
                if neighbor not in selected:
                    selected.add(neighbor)
                    pending.append(neighbor)
        chosen_profiles = {by_node[identity]["profile_id"] for identity in selected}
        chosen_roles = {by_profile[identity]["role"] for identity in chosen_profiles}
        payloads = [observations[identity] for identity in selected]
        payloads.extend(by_profile[profile_id] for profile_id in chosen_profiles)
        payloads.extend(actions[role] for role in chosen_roles)
        for payload in payloads:
            if _unresolved_reference(payload, known):
                return None
            selected.update(_references(payload, known))
        if len(selected) == before:
            break
    chosen_profiles = {by_node[identity]["profile_id"] for identity in selected}
    chosen_roles = {by_profile[identity]["role"] for identity in chosen_profiles}
    topology["devices"] = [node for node in nodes if node["id"] in selected]
    topology["connections"] = [edge for edge in topology["connections"]
                               if edge["source"]["device_id"] in selected
                               and edge["target"]["device_id"] in selected]
    value["catalog"]["profiles"] = [profile for profile in profiles
                                     if profile["profile_id"] in chosen_profiles]
    value["role_actions"] = {role: definition for role, definition in actions.items()
                             if role in chosen_roles}
    value["observations"]["devices"] = {identity: observation
                                           for identity, observation in observations.items()
                                           if identity in selected}
    return value


def project_operator_context(public_context):
    """Validate the full public tree first; use a full copy when closure is unclear."""
    value, _ = _snapshot(public_context, limit=_CONTEXT_BYTES, code="invalid_input")
    _context(value, "invalid_input")
    return _compact(value) or value
