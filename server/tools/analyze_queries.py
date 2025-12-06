#!/usr/bin/env python3
"""Analyze files for legacy SQLAlchemy query patterns.

This tool scans Python files to identify legacy SQLAlchemy query patterns
that need to be migrated to the modern select() API.

Usage:
    python server/tools/analyze_queries.py <file_path>
    python server/tools/analyze_queries.py server/controllers/api/auth.py

Output:
    Lists all legacy query patterns found with:
    - Line number
    - Pattern type
    - Complexity level
    - Modern replacement syntax
"""

import re
import sys
from pathlib import Path

# Pattern definitions with regex, modern replacement, and complexity level
PATTERNS = {
    "simple_get": {
        "pattern": r"session\.query\((\w+)\)\.get\(",
        "modern": "session.get(Model, id)",
        "complexity": "LOW",
        "description": "Simple primary key lookup",
    },
    "filter_first": {
        "pattern": r"session\.query\([^)]+\)\.filter\([^)]+\)\.first\(",
        "modern": "session.scalars(select(...).where(...)).first()",
        "complexity": "MEDIUM",
        "description": "Filter with single result",
    },
    "filter_all": {
        "pattern": r"session\.query\([^)]+\)\.filter\([^)]+\)\.all\(",
        "modern": "session.scalars(select(...).where(...)).all()",
        "complexity": "MEDIUM",
        "description": "Filter with multiple results",
    },
    "filter_by": {
        "pattern": r"session\.query\([^)]+\)\.filter_by\(",
        "modern": "session.scalars(select(...).filter_by(...)).first/all()",
        "complexity": "MEDIUM",
        "description": "Filter by keyword arguments",
    },
    "has_filter": {
        "pattern": r"\.has\(",
        "modern": "Same .has() in where() clause",
        "complexity": "MEDIUM",
        "description": "Relationship predicate filtering",
    },
    "with_entities": {
        "pattern": r"\.with_entities\(",
        "modern": "select(columns...) with session.execute().scalar()",
        "complexity": "MEDIUM-HIGH",
        "description": "Column selection/projection",
    },
    "composite_dict_get": {
        "pattern": r"session\.query\([^)]+\)\.get\(\{",
        "modern": "session.get(Model, (val1, val2)) or select().where()",
        "complexity": "MEDIUM-HIGH",
        "description": "Composite key lookup with dict",
    },
}


def analyze_file(filepath):
    """Analyze a Python file for legacy SQLAlchemy query patterns.

    Args:
        filepath: Path to the Python file to analyze

    Returns:
        List of dictionaries containing pattern matches with metadata
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    findings = []
    for name, config in PATTERNS.items():
        for match in re.finditer(config["pattern"], content):
            line_num = content[: match.start()].count("\n") + 1

            # Get the matched text (truncate if too long)
            matched_text = match.group(0)
            if len(matched_text) > 60:
                matched_text = matched_text[:60] + "..."

            findings.append(
                {
                    "line": line_num,
                    "pattern": name,
                    "text": matched_text,
                    "complexity": config["complexity"],
                    "modern": config["modern"],
                    "description": config["description"],
                }
            )

    # Sort by line number
    findings.sort(key=lambda x: x["line"])
    return findings


def print_findings(findings, filepath):
    """Pretty print the findings from analysis.

    Args:
        findings: List of finding dictionaries
        filepath: Path of the analyzed file
    """
    print(f"\n{'=' * 80}")
    print(f"SQLAlchemy Query Migration Analysis")
    print(f"File: {filepath}")
    print(f"{'=' * 80}\n")

    if not findings:
        print("✅ No legacy query patterns found! File is already migrated.\n")
        return

    print(f"Found {len(findings)} legacy query pattern(s):\n")

    # Group by complexity
    complexity_counts = {}
    for f in findings:
        complexity = f["complexity"]
        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1

    print("Complexity breakdown:")
    for complexity in ["LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"]:
        if complexity in complexity_counts:
            print(f"  {complexity:12s}: {complexity_counts[complexity]:3d} patterns")
    print()

    # Print each finding
    for i, f in enumerate(findings, 1):
        print(f"{i}. Line {f['line']:4d} [{f['complexity']:12s}] {f['description']}")
        print(f"   Pattern: {f['pattern']}")
        print(f"   Current: {f['text']}")
        print(f"   Modern:  {f['modern']}")
        print()


def main():
    """Main entry point for the analysis tool."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_queries.py <file_path>")
        print("\nExample:")
        print("  python server/tools/analyze_queries.py server/controllers/api/auth.py")
        sys.exit(1)

    filepath = sys.argv[1]

    # Validate file exists and is a Python file
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File does not exist: {filepath}")
        sys.exit(1)

    if path.suffix != ".py":
        print(f"Warning: File does not have .py extension: {filepath}")

    # Analyze the file
    findings = analyze_file(filepath)

    # Print results
    print_findings(findings, filepath)

    # Exit code indicates if patterns were found
    sys.exit(0 if not findings else 1)


if __name__ == "__main__":
    main()
