"""Closed, failure-sensitive inventory checks for host-surface-parity.

This module validates evidence declarations; it does not select a route or
assert that a host painted a surface. Callers supply executed evidence keyed
by receipt ID. A declaration alone can never satisfy an obligation.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import PurePosixPath
from typing import Any

LIFECYCLE = frozenset({"accept", "abort", "timeout", "validation_feedback_delivery"})
TRANSPORT_STATES = LIFECYCLE - {"accept"}
DELIVERY = {
    "informational_artifact": frozenset({"content_schema", "render", "destination", "delivery"}),
    "informational_delivery": frozenset({"content_schema", "destination", "delivery"}),
}
SUBJECT_KINDS = (
    frozenset(
        {
            "interactive_form",
            "interaction_transport",
            "interactive_workspace",
            "compatibility_endpoint",
        }
    )
    | DELIVERY.keys()
)
SURFACES = frozenset({"RICH", "PORTABLE", "HEADLESS"})
BASELINE_PATH = "docs/specs/host-surface-parity/producer_baseline.json"
BASELINE_SCHEMA = "attune.surface-inventory.producer-baseline/1"
BASELINE_REGEN = (
    'python -c "from pathlib import Path; from attune.elicitation.surface_inventory '
    f"import write_baseline; write_baseline(Path('.'), Path('{BASELINE_PATH}'))\""
    " — then re-derive subjects, delivery routes and obligations, refresh the pin, "
    "and review both diffs"
)


@dataclass(frozen=True)
class InventoryReport:
    """Inventory integrity is distinct from complete, executed parity evidence."""

    required_keys: frozenset[str]
    verified_keys: frozenset[str]
    pending_keys: frozenset[str]
    waived_keys: frozenset[str]
    registry_digest: str

    @property
    def complete(self) -> bool:
        """True only when every obligation has current executed evidence."""
        return self.required_keys == self.verified_keys


class SurfaceRegistryError(ValueError):
    """An inventory or evidence mismatch, naming the exact owning key."""


def canonical_digest(value: Any) -> str:
    """Hash canonical JSON without losing recursive keys, types or values."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_baseline_pin(registry: dict[str, Any], baseline: dict[str, Any]) -> None:
    """Bind the resolved reviewed fixture to its canonical path, schema and content."""
    pin = registry.get("producer_baseline")
    _require(
        isinstance(pin, dict) and set(pin) == {"path", "schema_version", "digest"},
        "producer_baseline",
        "expected exactly path, schema_version and digest",
    )
    _require(pin["path"] == BASELINE_PATH, "producer_baseline", "unexpected fixture path")
    _require(
        pin["schema_version"] == baseline.get("schema_version") == BASELINE_SCHEMA,
        "producer_baseline",
        "unknown or mismatched fixture schema_version",
    )
    expected, actual = pin["digest"], canonical_digest(baseline)
    _require(
        expected == actual,
        "producer_baseline",
        f"digest mismatch: expected {expected}; actual {actual}; regenerate with {BASELINE_REGEN}",
    )


def renderer_record_digest(record: dict[str, Any], target_id: str) -> str:
    """Bind an enhanced target and its twins without invalidating unrelated siblings."""
    targets = _index(record["targets"], "renderer target")
    _require(target_id in targets, record["id"], f"missing target {target_id}")
    selected = [targets[target_id]]
    for surface in ("PORTABLE", "HEADLESS"):
        twins = [t for t in targets.values() if t["surface"] == surface]
        _require(len(twins) == 1, record["id"], f"missing/duplicate {surface} twin")
        selected.extend(twins)
    return canonical_digest(
        {**{k: v for k, v in record.items() if k != "targets"}, "targets": selected}
    )


def _require(condition: bool, key: str, problem: str) -> None:
    if not condition:
        raise SurfaceRegistryError(f"{key}: {problem}")


def _collections(registry: dict, *names: str) -> None:
    for name in names:
        _require(isinstance(registry.get(name), list), name, "missing or invalid collection")


def _index(records: list[dict[str, Any]], namespace: str) -> dict[str, dict[str, Any]]:
    result = {}
    for record in records:
        _require(isinstance(record, dict), namespace, "record must be an object")
        key = record.get("id")
        _require(isinstance(key, str) and bool(key), namespace, "missing id")
        _require(key not in result, str(key), f"duplicate {namespace} id")
        result[key] = record
    return result


def producer_roots(baseline: dict[str, Any]) -> dict[str, list[str]]:
    """Map boundary roots to their detected anchors, preserving helper provenance."""
    reaching: dict[str, set[str]] = {}
    for edge in baseline["helper_edges"]:
        reaching.setdefault(edge["helper_anchor"], set()).add(edge["root_anchor"])
    roots: dict[str, set[str]] = {}
    for group in (
        "renderer_call_anchors",
        "package_host_envelope_anchors",
        "hook_envelope_anchors",
    ):
        for record in baseline[group]:
            anchor = record["anchor"]
            for root in reaching.get(anchor, {anchor}):
                roots.setdefault(root, set()).add(anchor)
    for artifact in baseline["artifacts"]:
        roots.setdefault(artifact["anchor"], set()).add(artifact["anchor"])
    return {key: sorted(value) for key, value in sorted(roots.items())}


def validate_producers(subjects: list[dict[str, Any]], baseline: dict[str, Any]) -> None:
    """Require one record per detected root, with every reaching helper preserved."""
    _index(subjects, "subject")
    for subject in subjects:
        _require(
            isinstance(subject.get("root_anchor"), str) and bool(subject["root_anchor"]),
            subject["id"],
            "missing root_anchor",
        )
    expected = producer_roots(baseline)
    actual = Counter(s["root_anchor"] for s in subjects if s.get("discovered", True))
    for anchor in sorted(set(expected) | set(actual)):
        _require(actual[anchor] == 1 and anchor in expected, anchor, "expected exactly one subject")
    for subject in subjects:
        if not subject.get("discovered", True):
            _require(
                subject["subject_kind"] == "interaction_transport"
                and subject["root_anchor"] == f"transport:{subject['id']}"
                and bool(subject.get("implementation_anchor")),
                subject["id"],
                "extra producer must be a declared transport, not a hidden root",
            )
            continue
        anchor = subject["root_anchor"]
        _require(
            subject.get("producer_anchors") == expected[anchor],
            anchor,
            f"producer provenance must equal {expected[anchor]}",
        )
        _validate_detected_footprint(subject, baseline)


def _validate_detected_footprint(subject: dict, baseline: dict) -> None:
    """Bind classifications to discovery, with explicit reviewed boundary exceptions."""
    anchor = subject["root_anchor"]
    anchors = subject["producer_anchors"]
    # These exceptions describe boundary behavior, not caller-controlled exemptions.
    overrides = {
        "src/attune/elicitation/ask_payload.py:form_to_ask_payload": "compatibility_endpoint",
        "src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_render_form": "compatibility_endpoint",
        "src/attune/mcp/server.py:AttuneMCPServer._register_resources": "informational_artifact",
        "src/attune/mcp/server.py:_handle_list_tools": "informational_artifact",
        "src/attune/mcp/workflow_handlers.py:_workflow_response": "informational_artifact",
        "src/attune/widgets/chart_widget_tool.py:render_chart_widget": "informational_artifact",
        "src/attune/elicitation/command_workspace.py:CommandWorkspaceRender.to_dict": "interactive_workspace",
    }
    detected = {
        row["subject_kind"]
        for group in ("hook_envelope_anchors", "package_host_envelope_anchors")
        for row in baseline[group]
        if row["anchor"] in anchors
    }
    kind = overrides.get(anchor)
    if kind is None:
        kind = next(
            (
                k
                for k in ("informational_delivery", "interactive_workspace", "interactive_form")
                if k in detected
            ),
            "informational_artifact" if anchor.startswith("artifact:") else "interactive_form",
        )
    _require(subject["subject_kind"] == kind, anchor, "detected subject kind changed")
    renderer_calls = {row["anchor"] for row in baseline["renderer_call_anchors"]}
    _require(
        kind != "informational_delivery" or not renderer_calls.intersection(anchors),
        anchor,
        "registered renderer cannot hide behind delivery classification",
    )
    _require(
        "informational_delivery" not in detected
        or not detected.intersection({"interactive_form", "interactive_workspace"}),
        anchor,
        "interactive envelope cannot hide behind hook delivery classification",
    )
    if kind in {"compatibility_endpoint", "informational_delivery"} or anchor.startswith(
        "artifact:"
    ):
        return
    metadata = anchor in {
        "src/attune/mcp/server.py:AttuneMCPServer._register_resources",
        "src/attune/mcp/server.py:_handle_list_tools",
    }
    if not metadata:
        required = (
            {"HEADLESS"}
            if anchor == "src/attune/mcp/server.py:AttuneMCPServer._handle_elicitation_ask"
            else SURFACES
        )
        actual = {t["surface"] for t in subject.get("targets", [])}
        _require(
            required <= actual,
            subject["id"],
            f"detected target footprint shrank: missing {', '.join(sorted(required - actual))}",
        )


def _validate_hook_routes(subject: dict, baseline: dict) -> None:
    anchors = subject.get("producer_anchors", [])
    hooks = [e for e in baseline["hook_envelope_anchors"] if e["anchor"] in anchors]
    if not hooks:
        return
    key = subject["id"]
    _require(subject["subject_kind"] == "informational_delivery", key, "hook delivery kind changed")
    expected = set()
    for hook in hooks:
        path = hook["anchor"].split(":", 1)[0]
        for registration in baseline["registrations"]:
            if (
                registration["resolved_repo_path"] == path
                and registration["event"] == hook["event"]
            ):
                expected.add(
                    (
                        hook["event"],
                        registration["matcher"],
                        hook["signature"],
                        hook["sink"],
                        hook["destination"],
                    )
                )
    fields = ("event", "matcher", "signature", "sink", "destination")
    actual = {tuple(route[k] for k in fields) for route in subject.get("delivery_routes", [])}
    _require(actual == expected, key, "event-qualified delivery routes differ from detected sinks")
    for route in subject["delivery_routes"]:
        _require(
            route["id"] == canonical_digest({field: route[field] for field in fields})[:16],
            key,
            "delivery route identity does not bind registration",
        )


def _route_refs(subject: dict[str, Any], subjects: dict, profiles: dict) -> None:
    sid = subject["id"]
    routes = set(subject["cold_routes"]) | set(subject["warm_routes"])
    refs = subject.get("route_transport_refs", {})
    _require(set(refs) == routes, sid, "route_transport_refs must equal cold/warm route union")
    for route, ref in refs.items():
        _require(set(ref) == {"kind", "id"}, sid, f"{route}: invalid typed reference")
        if route.startswith("host-native:"):
            pid = route.removeprefix("host-native:")
            _require(
                ref == {"kind": "host_profile", "id": pid} and pid in profiles,
                sid,
                f"{route}: wrong host profile",
            )
            continue
        target = subjects.get(ref["id"], {})
        _require(
            ref["kind"] == "subject" and target.get("subject_kind") == "interaction_transport",
            sid,
            f"{route}: wrong interaction transport",
        )
        if route.startswith("mcp-native:"):
            _require(
                target.get("transport_id") == route.removeprefix("mcp-native:"),
                sid,
                f"{route}: transport mismatch",
            )
        else:
            _require(route in SURFACES, sid, f"unknown route {route}")
        _require(
            sid in target.get("form_subject_ids", []),
            sid,
            f"{route}: one-way transport association",
        )


def _validate_subject(subject: dict[str, Any], subjects: dict, profiles: dict) -> None:
    sid, kind = subject["id"], subject["subject_kind"]
    _require(kind in SUBJECT_KINDS, sid, f"unknown subject_kind {kind}")
    if kind in DELIVERY:
        _require(
            not any(k in subject for k in ("cold_routes", "warm_routes", "route_transport_refs")),
            sid,
            "informational subject cannot own policy routes",
        )
        routes = subject.get("delivery_routes", [])
        _require(bool(routes), sid, "missing delivery_routes")
        _index(routes, f"{sid} delivery route")
        for route in routes:
            _require(
                set(route) == {"id", "event", "matcher", "signature", "sink", "destination"},
                sid,
                "delivery route must bind event/matcher/signature/sink/destination",
            )
            _require(
                route["id"] == canonical_digest({k: v for k, v in route.items() if k != "id"})[:16],
                sid,
                "delivery route identity does not bind content",
            )
        return
    if kind == "compatibility_endpoint":
        _require(
            not any(k in subject for k in ("cold_routes", "warm_routes", "route_transport_refs")),
            sid,
            "compatibility endpoint cannot own policy routes",
        )
        _require(bool(subject.get("compatibility_contract")), sid, "missing compatibility contract")
        return
    if kind == "interaction_transport":
        declared = subject.get("form_subject_ids", [])
        actual = {
            s["id"]
            for s in subjects.values()
            for r in s.get("route_transport_refs", {}).values()
            if r == {"kind": "subject", "id": sid}
        }
        _require(
            bool(actual) and len(declared) == len(set(declared)) and set(declared) == actual,
            sid,
            "orphan/one-way transport association",
        )
        return
    for context in ("cold_routes", "warm_routes"):
        routes = subject.get(context, [])
        _require(
            bool(routes) and len(routes) == len(set(routes)), sid, f"missing/duplicate {context}"
        )
        for route in routes:
            _require(
                route in SURFACES or route.startswith(("mcp-native:", "host-native:")),
                sid,
                f"unknown route {route}",
            )
    if kind == "interactive_form":
        _route_refs(subject, subjects, profiles)
    else:
        _require(
            "route_transport_refs" not in subject,
            sid,
            "workspace owns its lifecycle; delegated transport references are unsupported",
        )
    _enhanced(subject, f"subject:{sid}")
    surfaces = {t["surface"] for t in subject.get("targets", [])}
    routes = set(subject["cold_routes"]) | set(subject["warm_routes"])
    _require(routes & SURFACES <= surfaces, sid, "surface route has no declared target")
    _projection_targets(subject, routes)


def _projection_targets(subject: dict, routes: set[str]) -> dict[str, dict]:
    """Resolve optional exact route-to-subject projection bindings without waivers."""
    refs = subject.get("route_projection_targets")
    if refs is None:
        return {}
    sid = subject["id"]
    _require(
        isinstance(refs, dict) and set(refs) == routes, sid, "projection bindings must equal routes"
    )
    targets = _index(subject.get("targets", []), sid)
    resolved = {}
    for route, target_id in refs.items():
        _require(
            isinstance(target_id, str) and target_id in targets,
            sid,
            f"{route}: unknown projection target",
        )
        target = targets[target_id]
        expected = "HEADLESS" if route.startswith("mcp-native:") else route
        if route.startswith("host-native:"):
            expected = "host-native"
            _require(
                target_id == route.removeprefix("host-native:"), sid, "wrong host-native target"
            )
        _require(target["surface"] == expected, sid, f"{route}: wrong projection surface")
        resolved[route] = target
    return resolved


def _enhanced(owner: dict[str, Any], prefix: str) -> dict[str, dict[str, Any]]:
    obligations = {}
    targets = owner.get("targets", [])
    _index(targets, f"{prefix} target")
    surfaces = {t["surface"] for t in targets}
    for surface in SURFACES:
        _require(
            sum(t["surface"] == surface for t in targets) <= 1,
            prefix,
            f"duplicate {surface} target",
        )
    for target in targets:
        surface = target["surface"]
        _require(surface in SURFACES | {"host-native"}, prefix, f"unknown target surface {surface}")
        if surface not in {"RICH", "host-native"}:
            continue
        suffix = "surface:RICH" if surface == "RICH" else f"host-native:{target['id']}"
        key = f"{prefix}:{suffix}"
        for twin in ("PORTABLE", "HEADLESS"):
            _require(twin in surfaces, key, f"missing {twin} target")
        obligations[key] = {"kind": "parity", "obligation_key": key}
    return obligations


def required_obligations(registry: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Derive parity, owned lifecycle and qualified delivery keys; never count receipts."""
    _collections(registry, "subjects", "host_profiles", "renderers")
    subjects = _index(registry["subjects"], "subject")
    profiles = _index(registry["host_profiles"], "host profile")
    renderers = _index(registry["renderers"], "renderer")
    _require(bool(renderers), "renderers", "empty registry")
    result: dict[str, dict[str, str]] = {}
    for rid, record in renderers.items():
        result.update(_enhanced(record, f"renderer:{rid}"))
    for sid, subject in subjects.items():
        _validate_subject(subject, subjects, profiles)
        result.update(_enhanced(subject, f"subject:{sid}"))
        kind = subject["subject_kind"]
        if kind == "compatibility_endpoint":
            key = f"compatibility:subject:{sid}:production_response"
            result[key] = {"kind": "parity", "obligation_key": key}
        for route in sorted(
            set(subject.get("cold_routes", [])) | set(subject.get("warm_routes", []))
        ):
            key = f"route:{sid}:{route}:production_projection"
            result[key] = {"kind": "parity", "obligation_key": key}
        states = (
            {"accept"}
            if kind == "interactive_form"
            else (
                TRANSPORT_STATES
                if kind == "interaction_transport"
                else LIFECYCLE if kind == "interactive_workspace" else set()
            )
        )
        for state in sorted(states):
            result[f"lifecycle:subject:{sid}:{state}"] = {
                "kind": "lifecycle",
                "subject_id": sid,
                "state": state,
            }
        for route in subject.get("delivery_routes", []):
            for dimension in sorted(DELIVERY[kind]):
                key = f"delivery:{sid}:{route['id']}:{dimension}"
                result[key] = {
                    "kind": "delivery",
                    "subject_id": sid,
                    "route_id": route["id"],
                    "dimension": dimension,
                }
    for pid in profiles:
        for state in sorted(TRANSPORT_STATES):
            result[f"lifecycle:host_profile:{pid}:{state}"] = {
                "kind": "lifecycle",
                "host_profile_id": pid,
                "state": state,
            }
    return result


def _interval(entry: dict[str, Any]) -> tuple[date, date]:
    key = entry["id"]
    try:
        if not all(
            isinstance(entry.get(k), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry[k])
            for k in ("started_on", "expires_on")
        ):
            raise ValueError("dates must use YYYY-MM-DD")
        start, end = date.fromisoformat(entry["started_on"]), date.fromisoformat(
            entry["expires_on"]
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise SurfaceRegistryError(f"{key}: invalid UTC calendar dates") from exc
    _require(14 <= (end - start).days <= 30, key, "experiment interval must be 14–30 days")
    return start, end


def validate_experiments(
    registry: dict[str, Any], obligations: dict, today: date, *, baseline: dict[str, Any]
) -> set[str]:
    """Subtract only active exact parity keys after history, expiry and cap checks."""
    validate_baseline_pin(registry, baseline)
    _collections(registry, "experiments", "experiment_history", "experiment_exceptions", "receipts")
    active = _index(registry["experiments"], "experiment")
    history = _index(registry["experiment_history"], "experiment history")
    exceptions = _index(registry["experiment_exceptions"], "experiment exception")
    receipts = {
        r.get("obligation_key")
        for r in _index(registry["receipts"], "receipt").values()
        if r.get("kind") == "parity"
    }
    intervals: dict[str, list[tuple[date, date, str]]] = {}
    for eid, entry in history.items():
        _require(
            obligations.get(entry["obligation_key"], {}).get("kind") == "parity",
            eid,
            "unknown parity history obligation; a target rename cannot erase history",
        )
        start, end = _interval(entry)
        intervals.setdefault(entry["obligation_key"], []).append((start, end, eid))
    for key, rows in intervals.items():
        ordered = sorted(rows)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            _require(previous[1] < current[0], key, "overlapping/touching experiment history")
    waived: set[str] = set()
    for eid, entry in active.items():
        key = entry["obligation_key"]
        _require(
            obligations.get(key, {}).get("kind") == "parity",
            eid,
            f"unknown parity obligation {key}",
        )
        _require(key not in waived, key, "multiple active experiments")
        _require(key not in receipts, key, "experiment_receipt_conflict")
        _require(
            history.get(eid) == entry,
            eid,
            "active experiment must be appended atomically to history",
        )
        _require(
            bool(entry.get("owner")) and bool(entry.get("reason")), eid, "missing owner/reason"
        )
        root = PurePosixPath(entry["root_anchor"].split(":", 1)[0])
        _require(
            not root.is_absolute()
            and ".." not in root.parts
            and root.parts[:2] == ("experiments", "surface-parity"),
            eid,
            "root must be package-excluded experiments/surface-parity",
        )
        _require(
            not any(root.is_relative_to(PurePosixPath(p)) for p in baseline["shipped_roots"]),
            eid,
            "shipped experiment root",
        )
        start, end = _interval(entry)
        _require(start <= today < end, eid, "future-start or expired experiment")
        _check_rolling_cap(entry, intervals[key], exceptions)
        waived.add(key)
    for exception in exceptions.values():
        _require(
            exception.get("experiment_id") in active, exception["id"], "orphan experiment exception"
        )
    return waived


def _check_rolling_cap(entry: dict, rows: list, exceptions: dict) -> None:
    key, eid = entry["obligation_key"], entry["id"]
    days = {start + timedelta(days=i) for start, end, _ in rows for i in range((end - start).days)}
    start, end = _interval(entry)
    windows = {day for day in days if day < end and day + timedelta(days=180) > start}
    maximum = max(
        (sum(day <= other < day + timedelta(days=180) for other in days) for day in windows),
        default=0,
    )
    matches = [e for e in exceptions.values() if e.get("experiment_id") == eid]
    _require(len(matches) <= 1, eid, "duplicate exception")
    for exception in matches:
        _require(
            exception.get("obligation_key") == key
            and exception.get("implementation_digest") == entry.get("implementation_digest")
            and bool(exception.get("decision_ref")),
            eid,
            "exception binding mismatch",
        )
        _require(
            exception.get("started_on") == entry["started_on"]
            and exception.get("expires_on") == entry["expires_on"],
            eid,
            "exception interval mismatch",
        )
    _require(maximum <= 30 or bool(matches), key, "more than 30 waiver days in 180 days")


def validate_receipts(
    registry: dict[str, Any],
    obligations: dict,
    evidence: dict[str, dict],
    *,
    today: date,
    baseline: dict[str, Any],
) -> None:
    """Require exactly one executed, digest-bound receipt for each unwaived obligation."""
    _require(
        obligations == required_obligations(registry),
        "obligations",
        "caller obligations differ from registry",
    )
    waived = validate_experiments(registry, obligations, today, baseline=baseline)
    required = {k: v for k, v in obligations.items() if k not in waived}
    seen = _validate_receipt_rows(registry["receipts"], required, evidence)
    missing = set(required) - seen
    _require(not missing, sorted(missing)[0] if missing else "receipts", "missing receipt")


def _validate_receipt_rows(rows: list[dict], required: dict, evidence: dict) -> set[str]:
    receipts = _index(rows, "receipt")
    seen: set[str] = set()
    for rid, receipt in receipts.items():
        key = receipt.get("key", "")
        _require(key in required, key or rid, "orphan or waived receipt")
        _require(key not in seen, key, "duplicate obligation receipt")
        _require(rid == key.replace(":", "."), key, "receipt identity must bind obligation")
        seen.add(key)
        foreign_keys = {
            k: v
            for k, v in receipt.items()
            if k
            in {
                "kind",
                "obligation_key",
                "subject_id",
                "host_profile_id",
                "state",
                "route_id",
                "dimension",
            }
        }
        _require(foreign_keys == required[key], key, "wrong discriminated receipt foreign key")
        observed = evidence.get(rid)
        _require(observed is not None, key, "canonical evidence was not executed")
        digest_fields = {
            "implementation_digest",
            "fixture_digest",
            "record_digest",
            "normalization_digest",
            "result_digest",
        }
        _require(
            set(receipt)
            <= {"id", "key", "evidence_mode", "fixture"} | set(required[key]) | digest_fields,
            key,
            "unknown receipt field",
        )
        for field in ("evidence_mode", "fixture"):
            value = receipt.get(field)
            _require(
                isinstance(value, str) and bool(value.strip()) and value == observed.get(field),
                key,
                f"stale/missing {field}",
            )
        for name in (
            "implementation_digest",
            "fixture_digest",
            "record_digest",
            "normalization_digest",
            "result_digest",
        ):
            value = receipt.get(name)
            _require(
                isinstance(value, str)
                and bool(re.fullmatch(r"[0-9a-f]{64}", value))
                and value == observed.get(name),
                key,
                f"stale/missing {name}",
            )
    return seen


def validate_inventory(
    registry: dict[str, Any], baseline: dict[str, Any], evidence: dict[str, dict], *, today: date
) -> InventoryReport:
    """Validate a staged inventory without promoting pending declarations to receipts.

    The chair's increment-2 boundary allows explicitly owned runtime gaps for
    increment 3. They cannot waive package renderer evidence, overlap receipts
    or experiments, or satisfy ``route_evidence_missing``.
    """
    _require(
        registry.get("schema_version") == "attune.surface-parity/1",
        "registry",
        "unknown schema version",
    )
    validate_baseline_pin(registry, baseline)
    _collections(
        registry,
        "subjects",
        "host_profiles",
        "renderers",
        "receipts",
        "pending_obligations",
        "experiments",
        "experiment_history",
        "experiment_exceptions",
    )
    _require(
        not registry["experiments"] and not registry["experiment_exceptions"],
        "experiments",
        "live activation requires current artifact/decision verification; unavailable in increment 2",
    )
    validate_producers(registry["subjects"], baseline)
    for subject in registry["subjects"]:
        _require(
            subject.get("normalization_paths") == [],
            subject["id"],
            "local normalization is not yet receipted; semantic bindings cannot be removed",
        )
        _validate_hook_routes(subject, baseline)
    required = required_obligations(registry)
    _validate_renderer_receipt_owners(registry)
    waived = validate_experiments(registry, required, today, baseline=baseline)
    verified = _validate_receipt_rows(registry["receipts"], required, evidence)
    pending: set[str] = set()
    for row in registry["pending_obligations"]:
        _require(isinstance(row, dict), "pending_obligations", "record must be an object")
        key = row.get("key", "")
        _require(
            key in required and not key.startswith("renderer:"),
            key,
            "unknown or package-renderer pending obligation",
        )
        _require(key not in pending, key, "duplicate pending obligation")
        _require(
            key not in verified | waived,
            key,
            "pending obligation overlaps executed/experiment evidence",
        )
        _require(
            set(row) == {"key", "owner", "reason", "next_increment"}
            and bool(row["owner"])
            and bool(row["reason"])
            and row["next_increment"] == 3,
            key,
            "pending obligation requires owner/reason/increment 3",
        )
        pending.add(key)
    missing = set(required) - verified - waived - pending
    _require(not missing, sorted(missing)[0] if missing else "registry", "unaccounted obligation")
    report = InventoryReport(
        frozenset(required),
        frozenset(verified),
        frozenset(pending),
        frozenset(waived),
        canonical_digest(registry),
    )
    _require(
        registry.get("evidence_status") == ("complete" if report.complete else "incomplete"),
        "registry",
        "inventory success cannot claim complete parity",
    )
    return report


def _validate_renderer_receipt_owners(registry: dict) -> None:
    owners = {}
    for record in registry["renderers"]:
        for target in record["targets"]:
            surface = target["surface"]
            if surface not in {"RICH", "host-native"}:
                continue
            suffix = "surface:RICH" if surface == "RICH" else f"host-native:{target['id']}"
            key = f"renderer:{record['id']}:{suffix}"
            owners[key] = renderer_record_digest(record, target["id"])
    for receipt in _index(registry["receipts"], "receipt").values():
        key = receipt.get("key", "")
        if key in owners:
            _require(
                receipt.get("record_digest") == owners[key], key, "owning renderer record changed"
            )


def route_evidence_missing(
    registry: dict[str, Any], report: InventoryReport, subject_id: str, route: str
) -> frozenset[str]:
    """Return blockers for a declared route, including delegated lifecycle evidence.

    Pure evidence precondition for increment 3, not the capability/routing
    policy. Pending rows and experiment waivers are deliberately not proof.
    Until subject-to-renderer bindings exist, every package renderer obligation
    is conservatively required for every route, matching the inventory gate.
    The caller must supply the report returned by validate_inventory from trusted
    executed evidence. This value object is not an authentication token and must
    never be deserialized from an untrusted request as route authorization.
    """
    subjects = _index(registry["subjects"], "subject")
    _require(
        report.registry_digest == canonical_digest(registry), subject_id, "stale inventory report"
    )
    _require(subject_id in subjects, subject_id, "unknown route subject")
    subject = subjects[subject_id]
    if route in SURFACES:
        _require(
            route in {t["surface"] for t in subject.get("targets", [])},
            subject_id,
            "surface route has no declared target",
        )
    local_projection = f"route:{subject_id}:{route}:production_projection"
    _require(
        route in set(subject.get("cold_routes", [])) | set(subject.get("warm_routes", [])),
        subject_id,
        f"undeclared route {route}",
    )
    required = required_obligations(registry)
    _require(
        report.required_keys == frozenset(required),
        subject_id,
        "inventory report does not match required obligations",
    )
    keys = {key for key, ref in required.items() if ref.get("subject_id") == subject_id}
    projections = _projection_targets(
        subject, set(subject["cold_routes"]) | set(subject["warm_routes"])
    )
    if projections:
        target = projections[route]
        if target["surface"] == "RICH":
            keys.add(f"subject:{subject_id}:surface:RICH")
        elif target["surface"] == "host-native":
            keys.add(f"subject:{subject_id}:host-native:{target['id']}")
    else:
        keys.update(key for key in required if key.startswith(f"subject:{subject_id}:"))
    keys.add(local_projection)
    keys.update(key for key in required if key.startswith("renderer:"))
    transport = subject.get("route_transport_refs", {}).get(route)
    if transport:
        field = "subject_id" if transport["kind"] == "subject" else "host_profile_id"
        keys.update(key for key, ref in required.items() if ref.get(field) == transport["id"])
    return frozenset(keys - report.verified_keys)
