# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- MIT `LICENSE` file
- Comprehensive `README.md` with installation, usage, and control reference
- `CONTRIBUTING.md` for contributors
- `docs/ARCHITECTURE.md` describing module structure and rendering pipeline
- `docs/USAGE.md` with worked examples and a guide to swapping in custom DFAs
- Unit test suite under `tests/test_dfa.py`
- `pyproject.toml` metadata: description, keywords, license, dev dependencies,
  console-script entry point, and pytest configuration

### Changed
- Hardened `main.py` against display / font initialization failures and
  invalid input; added module- and class-level documentation
- `pyproject.toml` description replaced with a real summary

## [0.1.0] — 2026-05-07

### Added
- Animated visual simulator for a binary-input DFA accepting strings whose
  length is divisible by 3
- Auto and Step execution modes
- Token animation along Bézier-curved transitions, pulsing state highlight
- Accept / reject fade-in result banner