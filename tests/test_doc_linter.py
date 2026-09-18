# -*- coding: utf-8 -*-
"""
tests/test_doc_linter.py

Test suite for A2LDocLinter.
Verifies:
1. docs/tuning/stage1_bls_edc16u34_master_guide.md passes strict linting with 0 findings.
2. Non-existent A2L symbols in inline backticks and Mermaid diagrams are flagged.
3. Conceptual alias comments suppress unknown symbol warnings.
4. Unqualified physical assertions trigger UNQUALIFIED_PHYSICAL_CLAIM.
5. Controlled epistemic tags and Claim # citations satisfy qualification requirements.
"""

from pathlib import Path
import pytest

from tools.kb_a2l_doc_linter import A2LDocLinter, CONTROLLED_EPISTEMIC_TAGS


@pytest.fixture(scope="module")
def linter():
    return A2LDocLinter()


def test_doc_linter_passes_stage1_master_guide(linter):
    """The canonical Master Guide must pass strict linting with zero findings."""
    guide_path = Path("docs/tuning/stage1_bls_edc16u34_master_guide.md")
    assert guide_path.exists(), f"Master guide missing at {guide_path}"
    findings = linter.lint_file(guide_path)
    assert len(findings) == 0, f"Lint findings on master guide: {[str(f) for f in findings]}"


def test_doc_linter_flags_non_existent_symbol(linter, tmp_path):
    """Invented or non-existent symbols must be flagged with UNKNOWN_A2L_SYMBOL."""
    doc = tmp_path / "test_unknown_symbol.md"
    doc.write_text(
        "# Test Document\n\n"
        "Here we modify `Invented_FakeMap_MAP` to adjust fuelling.\n",
        encoding="utf-8",
    )
    findings = linter.lint_file(doc)
    assert len(findings) >= 1
    assert any(f.kind == "UNKNOWN_A2L_SYMBOL" and "Invented_FakeMap_MAP" in f.message for f in findings)


def test_doc_linter_respects_conceptual_alias(linter, tmp_path):
    """Declaring a conceptual alias must permit using the alias symbol without error."""
    doc = tmp_path / "test_alias.md"
    doc.write_text(
        "# Test Document\n\n"
        "<!-- conceptual-alias: Invented_FakeMap_MAP -> PCR_pBDesBas_MAP (Synthetic alias) -->\n\n"
        "Here we discuss `Invented_FakeMap_MAP` in conceptual context.\n",
        encoding="utf-8",
    )
    findings = linter.lint_file(doc)
    assert len(findings) == 0


def test_doc_linter_flags_mermaid_node_symbols(linter, tmp_path):
    """Symbols in Mermaid diagram nodes must be validated against A2L."""
    doc = tmp_path / "test_mermaid.md"
    doc.write_text(
        "# Pipeline\n\n"
        "```mermaid\n"
        "graph TD\n"
        '  A["PCR_pBDesBas_MAP"] --> B["Unregistered_Diagram_Symbol_MAP"]\n'
        "```\n",
        encoding="utf-8",
    )
    findings = linter.lint_file(doc)
    assert any(f.kind == "UNKNOWN_A2L_SYMBOL" and "Unregistered_Diagram_Symbol_MAP" in f.message for f in findings)


def test_doc_linter_flags_unqualified_physical_claim(linter, tmp_path):
    """Lines asserting physical figures with units must have controlled epistemic tags."""
    doc = tmp_path / "test_unqualified.md"
    doc.write_text(
        "# Tuning Strategy\n\n"
        "We set maximum boost pressure to 2350 mbar across the upper load range.\n",
        encoding="utf-8",
    )
    findings = linter.lint_file(doc)
    assert any(f.kind == "UNQUALIFIED_PHYSICAL_CLAIM" for f in findings)


@pytest.mark.parametrize("tag", sorted(CONTROLLED_EPISTEMIC_TAGS))
def test_doc_linter_accepts_controlled_epistemic_tags(linter, tmp_path, tag):
    """Every authorized epistemic tag satisfies the qualification requirement."""
    doc = tmp_path / f"test_tag_{tag.strip('[]')}.md"
    doc.write_text(
        f"# Tuning Strategy\n\n"
        f"Maximum boost pressure is 2350 mbar {tag} for BV39.\n",
        encoding="utf-8",
    )
    findings = linter.lint_file(doc)
    assert len(findings) == 0


def test_doc_linter_accepts_claim_citation(linter, tmp_path):
    """Citing a formal Claim # satisfies qualification requirement."""
    doc = tmp_path / "test_claim_citation.md"
    doc.write_text(
        "# Tuning Strategy\n\n"
        "Maximum boost pressure continuous envelope is 2350 mbar (see Claim #83).\n",
        encoding="utf-8",
    )
    findings = linter.lint_file(doc)
    assert len(findings) == 0
