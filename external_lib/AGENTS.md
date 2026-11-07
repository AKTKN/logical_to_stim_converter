# AGENTS.md — External references

This directory holds **read-only local third-party source references**, ignored by Git by default. The actual content may be absent. The new package must not rely on undeclared machine-specific paths.

Before implementing an adapter: inspect upstream source/API, record repository URL and commit in `STATUS.md`, keep upstream modifications separate from package modifications, and test the adapter against that revision. Prefer public `stimflow` behavior over monkey-patching/private methods. Do not automatically commit/vendor external code.
