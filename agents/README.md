# Agent Definitions

This directory contains specialized agent definitions imported from [duck-soup](https://github.com/schuyler/duck-soup).

## Available Agents

### Groucho - Project Architect
**Purpose**: Provides architectural guidance and ensures implementation decisions align with existing project patterns.

**Use when**:
- Starting a new feature requiring understanding of project patterns
- Evaluating implementation approaches for consistency
- Determining where new code should be placed
- Making architectural decisions affecting multiple parts of the codebase

**Location**: `agents/groucho.md`

### Chico - Code Reviewer
**Purpose**: Performs thorough code reviews to verify implementations meet requirements and maintain quality standards.

**Use when**:
- Code has been written or modified
- After completing a logical chunk of work
- Before considering work complete
- Need to verify implementation matches requirements

**Location**: `agents/chico.md`

### Zeppo - Debugging Specialist
**Purpose**: Investigates and resolves bugs through systematic root cause analysis.

**Use when**:
- Encountering runtime errors or unexpected behavior
- Test failures need investigation
- After implementing new features (proactive verification)
- Bugs need systematic investigation

**Location**: `agents/zeppo.md`

### Harpo - Documentation Specialist
**Purpose**: Creates and maintains project documentation with strict factual language standards.

**Use when**:
- Features completed that need documentation
- Code needs comments or docstrings
- Bug fixes should be documented
- Architecture or design decisions need capture
- Existing documentation is stale
- New project documentation needed

**Location**: `agents/harpo.md`

## Usage

These agents can be invoked in two ways:

### Method 1: Direct Application
Read the agent definition and apply its methodology directly to the task at hand.

### Method 2: Task Tool Invocation
Use the Task tool with `subagent_type="general-purpose"` and pass the agent's prompt content along with the specific task context.

## Agent Structure

Each agent file contains:
- **YAML frontmatter**: Metadata including name, description, tools, model preference, and color
- **Prompt body**: Detailed instructions, methodology, and output format for the agent

## Customization

These agents can be modified to better fit corazonn's specific needs:
- Adjust tools available
- Modify output formats
- Adapt methodologies for hardware/firmware development
- Add project-specific conventions
