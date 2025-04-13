# System Refiner Specific Memory

## Analysis Findings
<!-- Append findings from logs/feedback/config using the format below -->

### Finding: User Feedback - [2025-04-12 22:27:48]
- **Source**: `sparc-feedback.md` ([2025-04-08 12:41:22]), `code-feedback.md` ([2025-04-08 10:24:16])
- **Observation**: Modes (SPARC, Code) provided overly brief summaries upon task completion, requiring follow-up prompts.
- **Initial Analysis**: Indicates a need for clearer system-wide expectations or instructions regarding completion summary detail.

### Finding: User Feedback - [2025-04-12 22:27:48]
- **Source**: `sparc-feedback.md` ([2025-04-11 15:21:17])
- **Observation**: Initial project workflow lacked a standardized git commit step after feature completion cycles.
- **Initial Analysis**: Highlights a gap in the standard SPARC workflow definition. SPARC learned to delegate this, but it should be formalized.

### Finding: User Feedback / Workflow Analysis - [2025-04-12 22:27:48]
- **Source**: `code-feedback.md` ([2025-04-12 05:29:25]), User Task Context (Chorus regression), `activeContext.md` (Regression fixes logged)
- **Observation**: Regressions were introduced after fixes/features were implemented, sometimes caught later. Code mode initially only ran module-specific tests.
- **Initial Analysis**: Suggests testing scope might be too narrow during development steps, increasing the risk of uncaught regressions.

### Finding: User Feedback - [2025-04-12 22:27:48]
- **Source**: `tdd-feedback.md` ([2025-04-12 17:59:47]), `code-feedback.md` ([2025-04-12 18:02:42])
- **Observation**: Multiple modes (TDD, Code) repeatedly used incorrect XML format for tool invocation (e.g., `<tool_name>list_files</tool_name>`).
- **Initial Analysis**: Points to potential ambiguity or misinterpretation of the system's instructions on tool usage format.

### Finding: User Task Context / Workflow Analysis - [2025-04-12 22:27:48]
- **Source**: User Task Context, `sparc.md` (Delegations Log), `.clinerules-sparc`
- **Observation**: User perceived SPARC not reading specification files directly as a friction point. Logs show SPARC delegates spec/architecture tasks and likely consumes their structured output via Memory Bank.
- **Initial Analysis**: This might be a misunderstanding of SPARC's orchestration role versus direct file parsing. Clarification in documentation might be needed.

## Identified Patterns & Bottlenecks
<!-- Append identified systemic issues using the format below -->

### Pattern/Bottleneck: Insufficient Summary Detail - [2025-04-12 22:27:48]
- **Description**: Modes completing tasks often provide summaries that lack sufficient detail about actions taken, results, and status, necessitating follow-up questions from the user or orchestrator.
- **Evidence**: Finding [User Feedback - [2025-04-12 22:27:48]] (Source: `sparc-feedback.md`, `code-feedback.md`)
- **Impact**: Increased interaction cycles, reduced workflow efficiency.
- **Hypothesized Cause(s)**: Lack of explicit instruction in mode definitions (`.roomodes`) or core system prompts regarding required summary detail level.

### Pattern/Bottleneck: Missing Formalized Version Control - [2025-04-12 22:27:48]
- **Description**: The standard workflow initially did not include a mandatory version control (git commit) step after the completion of a full feature cycle (implementation, test, refactor, docs).
- **Evidence**: Finding [User Feedback - [2025-04-12 22:27:48]] (Source: `sparc-feedback.md`), `sparc.md` log showing later addition of commit delegations.
- **Impact**: Lack of consistent version history, difficulty tracking feature completion, potential for lost work.
- **Hypothesized Cause(s)**: Omission in the defined SPARC methodology or SPARC mode's core instructions.

### Pattern/Bottleneck: Regression Risk due to Incomplete Testing - [2025-04-12 22:27:48]
- **Description**: Implementing fixes or new features sometimes introduces regressions in other parts of the system, which are not always caught immediately. This seems linked to modes running only module-specific tests instead of the full test suite.
- **Evidence**: Finding [User Feedback / Workflow Analysis - [2025-04-12 22:27:48]] (Source: `code-feedback.md`, User Context, `activeContext.md`)
- **Impact**: Reduced system stability, increased debugging time, rework.
- **Hypothesized Cause(s)**: Lack of explicit requirement in mode instructions (`.roomodes` for code/debug, `.clinerules-tdd`) to run the full test suite after potentially impactful changes.

### Pattern/Bottleneck: Incorrect Tool Usage Format - [2025-04-12 22:27:48]
- **Description**: Modes repeatedly failed to use the correct XML syntax for tool invocation, despite examples being provided.
- **Evidence**: Finding [User Feedback - [2025-04-12 22:27:48]] (Source: `tdd-feedback.md`, `code-feedback.md`)
- **Impact**: Failed tool calls, workflow interruptions, requires user/system correction.
- **Hypothesized Cause(s)**: Ambiguous phrasing in the core system prompt or mode instructions explaining the required format. LLM misinterpretation.

### Pattern/Bottleneck: Expectation Mismatch on Specification Handling - [2025-04-12 22:27:48]
- **Description**: User expected SPARC orchestrator to read raw specification documents directly, whereas the system appears designed for SPARC to consume structured outputs from specialist modes (`spec-pseudocode`, `architect`) via the Memory Bank.
- **Evidence**: Finding [User Task Context / Workflow Analysis - [2025-04-12 22:27:48]] (Source: User Context, `sparc.md`, `.clinerules-sparc`)
- **Impact**: Potential user confusion or frustration if workflow expectations are not met.
- **Hypothesized Cause(s)**: Lack of clear documentation explaining SPARC's orchestration model and reliance on Memory Bank for inter-mode communication.

## Improvement Proposals
<!-- Append detailed proposals using the format below -->

### Improvement Proposal: Enhance Summary Requirements - [2025-04-12 22:27:48]
- **Problem Addressed**: Pattern/Bottleneck: Insufficient Summary Detail - [2025-04-12 22:27:48]
- **Proposed Change**: Modify `customInstructions` in `.roomodes` for all action-performing modes (Code, TDD, Debug, Refinement, Docs, Integration, DevOps, QA, etc.) to explicitly mandate detailed summaries in `attempt_completion`. Summaries should include: key changes made, files affected, test results (pass/fail counts, specific failures if any), confirmation of adherence to constraints (e.g., file size), and clear status/next steps. Consider updating the core system prompt as well.
- **Target File(s)**: `.roomodes`, potentially core system prompt.
- **Rationale**: Reduces ambiguity and follow-up questions, improves workflow efficiency, ensures SPARC has necessary context.
- **Potential Impact/Benefit**: Smoother handoffs between modes, less user intervention needed.
- **Status**: Proposed

### Improvement Proposal: Formalize Git Commit Step - [2025-04-12 22:27:48]
- **Problem Addressed**: Pattern/Bottleneck: Missing Formalized Version Control - [2025-04-12 22:27:48]
- **Proposed Change**: Update SPARC's core instructions (in `.roomodes` or `.clinerules-sparc`) to mandate a `git commit` step after each full feature cycle (implementation, testing, refactoring, documentation). This step should typically be delegated to `devops` mode, and the commit message should reference the completed task/requirement ID. Define "full feature cycle" clearly.
- **Target File(s)**: `.roomodes` (sparc mode), `.clinerules-sparc`.
- **Rationale**: Enforces consistent version control hygiene, improves traceability and project history.
- **Potential Impact/Benefit**: Better project state management, easier rollbacks or reviews.
- **Status**: Proposed

### Improvement Proposal: Mandate Full Test Suite Runs - [2025-04-12 22:27:48]
- **Problem Addressed**: Pattern/Bottleneck: Regression Risk due to Incomplete Testing - [2025-04-12 22:27:48]
- **Proposed Change**: Modify `customInstructions` in `.roomodes` for `code` and `debug` modes. Require running the *full* project test suite (e.g., `poetry run pytest`) before calling `attempt_completion` for any changes that modify shared code or interfaces, or fix bugs with potential side effects. Update `.clinerules-tdd` to emphasize full suite verification during the Refactor phase.
- **Target File(s)**: `.roomodes` (code, debug), `.clinerules-tdd`.
- **Rationale**: Increases likelihood of catching regressions early, improves overall system stability.
- **Potential Impact/Benefit**: Fewer bugs introduced, reduced debugging time later in the cycle.
- **Status**: Proposed

### Improvement Proposal: Clarify Tool Usage Instructions - [2025-04-12 22:27:48]
- **Problem Addressed**: Pattern/Bottleneck: Incorrect Tool Usage Format - [2025-04-12 22:27:48]
- **Proposed Change**: 1. Review and revise the core system prompt's explanation of tool usage XML format for clarity. Replace potentially ambiguous phrases with direct instructions and clear examples (e.g., "Use the format `<tool_name><parameter>value</parameter></tool_name>`, like `<read_file><path>src/main.py</path></read_file>`."). 2. Add a concise reminder about the correct format to `customInstructions` in `.roomodes` for modes observed making errors (TDD, Code).
- **Target File(s)**: Core system prompt (requires system modification access), `.roomodes` (tdd, code).
- **Rationale**: Aims to eliminate tool format errors caused by misinterpretation of instructions.
- **Potential Impact/Benefit**: Fewer failed tool calls, smoother workflow, less need for correction.
- **Status**: Proposed

### Improvement Proposal: Document SPARC's Specification Handling - [2025-04-12 22:27:48]
- **Problem Addressed**: Pattern/Bottleneck: Expectation Mismatch on Specification Handling - [2025-04-12 22:27:48]
- **Proposed Change**: Add a section to SPARC's system documentation (or potentially within `.clinerules-sparc` or `.roomodes` description for SPARC) clarifying its orchestration role. Explain that SPARC relies on specialist modes (`spec-pseudocode`, `architect`) to process requirements and designs, storing structured outputs in the Memory Bank, which SPARC then uses for delegation, rather than parsing raw specification documents itself.
- **Target File(s)**: System documentation (e.g., a `SPARC_Overview.md`), `.clinerules-sparc`, `.roomodes` (sparc mode).
- **Rationale**: Manages user expectations about SPARC's capabilities and workflow, clarifies the importance of specialist modes and the Memory Bank.
- **Potential Impact/Benefit**: Reduced user confusion, better alignment on how to interact with SPARC for specification-related tasks.
- **Status**: Proposed

## Delegated Implementation Tasks
<!-- Append tasks delegated to system-modifier using the format below -->