workspace "Codex Skill Router Artifact Guard" "Fail-closed staging, hash verification, exclusive lease, atomic commit, rollback, and audit for machine-global router files." {
  model {
    operator = person "Operator" "Authorizes proposed transactions, reviews failures, and owns the live global root."

    csr = softwareSystem "Codex Skill Router" "Local advisory skill router and its governed machine-global artifact transaction boundary." {
      guard = container "Artifact Guard" "Owns one Transaction aggregate: content-addressed staging, source/pre/post hash checks, exclusive root lease, atomic commit or rollback, and audit append." "Python"
      source = container "Canonical Source" "Repository-owned Python, Markdown, JSON, and hash-manifest files that can be selected for guarded installation." "Python/JSON/Markdown"
      tests = container "Portable Test Harness" "Runs real filesystem integration and contention cases against temporary roots without mutating the operator live root." "Python"
      stage = container "Immutable Stage Store" "Content-addressed immutable bytes retained as evidence." "Local filesystem" "Database"
      lease = container "Root Lease Store" "Exclusive compare-and-set ownership and bounded stale-owner metadata for one root." "Local filesystem" "Database"
      audit = container "Transaction Audit Log" "Append-only terminal transaction outcomes and hash bundles." "JSONL" "Database"
    }

    liveRoot = softwareSystem "Machine-Global Skill Router Root" "/Users/speed/.codex/skill-router; deliberately outside Git and writable only through the guard." "External"

    operator -> guard "Proposes guarded transaction or verify-only inspection" "CLI"
    guard -> source "Reads canonical bytes" "Python file I/O"
    guard -> stage "Seals immutable bytes" "atomic create/read-only"
    guard -> lease "Acquires/releases one root lease" "atomic file create"
    guard -> liveRoot "Verifies pre-state, backs up, atomically replaces, verifies post-state" "atomic filesystem operations"
    guard -> audit "Appends terminal evidence" "JSONL append"
    tests -> guard "Exercises success, contention, stale hash, rollback, and recovery paths" "Python API"
    tests -> stage "Confirms loser bytes remain immutable evidence" "read-only"
    tests -> audit "Replays terminal outcomes" "read-only"
  }

  views {
    systemContext csr "Context" {
      include *
      autoLayout lr
    }
    container csr "Containers" {
      include *
      autoLayout lr
    }
    styles {
      element "Person" { shape Person background "#438DD5" color "#ffffff" }
      element "Software System" { background "#2E6295" color "#ffffff" }
      element "Container" { background "#438DD5" color "#ffffff" }
      element "Database" { shape Cylinder }
      element "External" { background "#8E8E93" color "#ffffff" }
    }
  }
}
