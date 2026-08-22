"""Tests de integridad del repo (sin datos externos ni freqtrade).

Gate mínimo de CI: la estructura es la prometida y los scripts compilan.
No requiere klines ni credenciales.
"""
import os
import py_compile
import ast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED_DIRS = ["scripts", "strategies", "tests"]
README_REQUIRED = ["fuente de verdad", "STATUS.md"]
PROJECT_REQUIRED = ["fuente de verdad", "GitHub = fuente de verdad"]


def test_required_dirs_exist():
    for d in EXPECTED_DIRS:
        assert os.path.isdir(os.path.join(ROOT, d)), f"falta {d}/"


def test_scripts_compile():
    bad = []
    for sub in ["scripts", "strategies", "tests"]:
        for root, _, files in os.walk(os.path.join(ROOT, sub)):
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(root, f)
                    try:
                        py_compile.compile(p, doraise=True)
                    except py_compile.PyCompileError:
                        bad.append(p)
    assert not bad, f"no compilan: {bad}"


def test_readme_mentions_source_of_truth():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        t = fh.read()
    for token in README_REQUIRED:
        assert token in t, f"README.md no menciona '{token}'"


def test_project_mentions_source_of_truth():
    with open(os.path.join(ROOT, "PROJECT.md"), encoding="utf-8") as fh:
        t = fh.read()
    for token in PROJECT_REQUIRED:
        assert token in t, f"PROJECT.md no menciona '{token}'"


def test_no_placeholder_tokens_in_committed_code():
    """Nunca debe quedar un placeholder de token en el repo versionado."""
    offenders = []
    for sub in ["scripts", "strategies", "tests", "."]:
        if sub == ".":
            candidates = [f for f in os.listdir(ROOT) if f.endswith(".md")]
        else:
            candidates = []
            for root, _, files in os.walk(os.path.join(ROOT, sub)):
                candidates += [os.path.join(root, f) for f in files if f.endswith(".py")]
        for p in candidates:
            if "***" in p or "***@" in p:
                offenders.append(p)
    assert not offenders, f"placeholder de token encontrado: {offenders}"
