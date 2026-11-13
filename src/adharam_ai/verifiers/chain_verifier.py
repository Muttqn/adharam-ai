"""Chain-of-Title Directed Acyclic Graph (DAG) & Survey Subdivision Matcher."""

from __future__ import annotations

import re

import networkx as nx

from adharam_ai.schemas.deed_record import DeedRecord
from adharam_ai.schemas.risk_report import ChainLinkIssue, ChainVerificationResult


def normalize_survey_token(survey_no: str) -> str:
    """Normalize survey strings (e.g., 'Sy. No. 42/3 A 1' -> '42/3A1')."""
    cleaned = re.sub(r"(?i)\b(re-?sy|sy|no|block)\b", "", survey_no)
    return re.sub(r"[\s\-.]+", "", cleaned).upper()


def is_survey_subdivision_compatible(parent_survey: str, child_survey: str) -> bool:
    """Check if child_survey is identical to or a valid subdivision of parent_survey.

    Examples:
        ('42/3', '42/3A1') -> True
        ('118/4', '118/4B') -> True
        ('42/3', '43/1') -> False
    """
    parent = normalize_survey_token(parent_survey)
    child = normalize_survey_token(child_survey)
    if not parent or not child:
        return False
    if parent == child:
        return True
    return child.startswith(parent) and len(child) > len(parent)


def _deed_key(doc_number: str, sro_name: str) -> str:
    sro_norm = re.sub(r"\s+", " ", sro_name.strip().upper())
    return f"{doc_number.strip()}::{sro_norm}"


def verify_chain_of_title(deeds: list[DeedRecord]) -> ChainVerificationResult:
    """Build and verify the Chain-of-Title DAG across uploaded deeds.

    Nodes are registered deeds sorted chronologically; edges point from
    prior deed (Munnadharam) -> subsequent deed.
    """
    if not deeds:
        raise ValueError("Cannot verify chain of title on empty deed list.")

    sorted_deeds = sorted(deeds, key=lambda d: d.registration_meta.execution_date)
    present_deed = sorted_deeds[-1]
    present_doc_num = present_deed.registration_meta.doc_number.value

    deed_by_key: dict[str, DeedRecord] = {}
    graph = nx.DiGraph()

    for deed in sorted_deeds:
        doc_num = deed.registration_meta.doc_number.value
        key = _deed_key(doc_num, deed.registration_meta.sro_name)
        deed_by_key[key] = deed
        graph.add_node(
            key,
            doc_number=doc_num,
            execution_date=deed.registration_meta.execution_date,
        )

    issues: list[ChainLinkIssue] = []

    for deed in sorted_deeds:
        child_doc = deed.registration_meta.doc_number.value
        child_key = _deed_key(child_doc, deed.registration_meta.sro_name)

        for prior in deed.prior_deeds_cited:
            parent_key = _deed_key(prior.doc_number, prior.sro_name)
            if parent_key not in deed_by_key:
                issues.append(
                    ChainLinkIssue(
                        issue_type="MISSING_LINK_DEED",
                        source_doc_number=child_doc,
                        referenced_doc_number=prior.doc_number,
                        detail=(
                            f"Deed {child_doc} cites Munnadharam {prior.doc_number} "
                            f"({prior.sro_name}), which is missing from the dossier."
                        ),
                    )
                )
                continue

            parent_deed = deed_by_key[parent_key]
            graph.add_edge(parent_key, child_key)

            parent_sy = parent_deed.property_schedule.old_survey_no
            child_sy = deed.property_schedule.old_survey_no
            if not is_survey_subdivision_compatible(parent_sy, child_sy):
                issues.append(
                    ChainLinkIssue(
                        issue_type="SURVEY_SUBDIVISION_MISMATCH",
                        source_doc_number=child_doc,
                        referenced_doc_number=prior.doc_number,
                        detail=(
                            f"Old Survey mismatch: parent deed {prior.doc_number} covers "
                            f"Sy. No. {parent_sy}, but {child_doc} recites {child_sy}."
                        ),
                    )
                )

    if not nx.is_directed_acyclic_graph(graph):
        issues.append(
            ChainLinkIssue(
                issue_type="CYCLE_DETECTED",
                source_doc_number=present_doc_num,
                detail="Circular Munnadharam reference detected in title chain.",
            )
        )
        chronological = [d.registration_meta.doc_number.value for d in sorted_deeds]
    else:
        ordered_keys = list(nx.topological_sort(graph))
        chronological = [graph.nodes[k]["doc_number"] for k in ordered_keys]

    root_keys = [n for n, deg in graph.in_degree() if deg == 0]
    root_docs = [graph.nodes[k]["doc_number"] for k in root_keys]

    # Check if any earlier deed is disconnected from the present deed
    if nx.is_directed_acyclic_graph(graph) and len(sorted_deeds) > 1:
        present_key = _deed_key(present_doc_num, present_deed.registration_meta.sro_name)
        ancestors = nx.ancestors(graph, present_key) | {present_key}
        for key in graph.nodes:
            if key not in ancestors:
                orphan_doc = graph.nodes[key]["doc_number"]
                issues.append(
                    ChainLinkIssue(
                        issue_type="ORPHAN_DEED",
                        source_doc_number=orphan_doc,
                        detail=(
                            f"Deed {orphan_doc} is not linked to the present title deed "
                            f"{present_doc_num}."
                        ),
                    )
                )

    return ChainVerificationResult(
        is_complete=len(issues) == 0,
        chronological_doc_numbers=chronological,
        root_doc_numbers=root_docs,
        present_doc_number=present_doc_num,
        issues=issues,
    )
