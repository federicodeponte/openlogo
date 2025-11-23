# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.4] - 2025-11-22

### Fixed
- **CRITICAL:** Updated package version in pyproject.toml from 0.1.0 to 0.1.4 (was 3 releases behind!)
- Fixed pytest-asyncio deprecation warning (added `asyncio_default_fixture_loop_scope = "function"`)
- Moved internal development docs to `docs/archive/` (ARCHITECTURE_DECISION, TEST_REPORT, etc.)
- Removed empty `tests/e2e/` directory (no E2E tests exist yet)
- Added test result files to `.gitignore` (scaile_results.json, results_city_map.json)

### Changed
- **README now honestly discloses:**
  - Alpha status badge
  - 19% test coverage (not "comprehensive")
  - What's tested and what's not
  - Async/OpenAI integration is NOT tested
  - E2E tests don't exist
- Improved badge URL to use specific workflow file (more reliable)

### Documentation
- Added Testing section to README with honest coverage metrics
- Archived 5 internal docs (51KB) to docs/archive/
- Clear warning about alpha status and production readiness

## [0.1.3] - 2025-11-22

### Fixed
- Removed `.coverage` binary file from repository (added to .gitignore)
- Fixed regex deprecation warning in logo_crawler.py (use raw string)
- Updated CI to run full test suite (all tests, not just unit tests)
- Removed broken Codecov upload step (no token configured)
- Removed broken PyPI release workflow (not yet configured)

### Changed
- CI now runs 12 tests (11 unit + 1 integration), 1 skipped
- Cleaner repository with no binary artifacts

## [0.1.2] - 2025-11-22

### Fixed
- Fixed macOS CI cairo library loading by adding PKG_CONFIG_PATH and DYLD_LIBRARY_PATH
- Applied black code formatting to all Python files

## [0.1.1] - 2025-11-22

### Fixed
- Unit tests now properly match actual implementation
- Fixed `is_valid_image_size()` tests to use PIL Image objects
- Fixed `extract_confidence_score()` tests to match regex-based extraction
- Fixed `extract_description()` tests to match actual parsing logic
- All tests now pass (12 passed, 1 skipped)

## [0.1.0] - 2025-11-22

### Added
- First release of crawl4logo
- Logo extraction from company websites
- Support for multiple search strategies
- Comprehensive test coverage
