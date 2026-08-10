#!/usr/bin/env python3
"""Test script to verify HTML file content."""
from pathlib import Path

html_path = Path(__file__).resolve().parent / "sudoku_ui.html"
print(f"Reading from: {html_path}")
print(f"File exists: {html_path.exists()}")

html_content = html_path.read_text(encoding="utf-8")
print(f"File size: {len(html_content)} bytes")

# Check for color-scheme
if "color-scheme: light" in html_content:
    print("✓ Found: color-scheme: light")
elif "color-scheme: dark" in html_content:
    print("✗ Found: color-scheme: dark")
else:
    print("? color-scheme not found")

# Check for white background
if "background: #f5f5f5" in html_content:
    print("✓ Found: background: #f5f5f5 (light)")
elif "linear-gradient(135deg" in html_content:
    print("✗ Found: linear-gradient (dark)")
else:
    print("? background style not found")

print("\nFirst 600 chars:")
print(html_content[:600])
