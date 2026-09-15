# How common is this, actually

The reproductions in this repository show five products failing open. That
says nothing about whether the failure is rare or everywhere. This file is the
attempt to bound it, because a defect class with no prevalence estimate is an
anecdote.

Four measurements, each independently checkable.

## 1. Mature reviewed code: 0 findings in 1,128,865 lines

Scanned with a detector written specifically for one shape of this defect, a
security check whose result is computed and then never read.

| project | why it was chosen |
|---|---|
| certbot | issues TLS certificates, heavily reviewed |
| bandit | a security linter, so its own guards matter |
| pyjwt | token verification |
| sigstore-python | signature verification |
| python-tuf | update framework, adversarial threat model |
| detect-secrets | scanning |

1,128,865 lines, 48,925 functions, 3,741 files. **Zero findings**, in both
strict and relaxed modes.

The zero is not an artifact of the detector failing to run. 8,463 assignments
matched the name pattern it looks for, and in every single case the value was
subsequently read. The detector was also run with a corpus of known-positive
cases planted inside an 802K-line repository and surfaced all of them, so the
walk reaches files at scale.

## 2. Young enforcement code: 14 findings in 36 projects

Same defect class, found by reading rather than by the detector, in projects
whose enforcement code was written in roughly the last eighteen months.

Confirmed, each with a reproduction run against the shipped package:
litellm (two separate guardrails), deepeval, guardrails-ai,
openai-agents-python, microsoft/autogen, stacklok/toolhive, and five more
under private disclosure at the time of writing.

Two further confirmed instances are not counted as disclosures, because
neither project left a channel to report through. AutoGPT's `classic/` Agent
Protocol server: the maintainers' own SECURITY.md lists that directory as
explicitly out of scope ("unsupported... avoid use of deprecated
components"). Rebuff's LLM detection tactic: the repository has been
archived since 2024 and never had a SECURITY.md. Both are included in the
count because they are real, reproduced instances of the pattern, not
because either was ever actionable as a vulnerability report.

Read and found clean, listed because a survey that finds a defect everywhere it
looks is measuring the surveyor: langchain, langgraph, crewAI, letta-code,
braintrust autoevals, Arize phoenix, comet opik, langfuse, the MCP filesystem
server, the MCP Python SDK, mcp-agent, block/goose, NVIDIA SkillSpector,
microsoft/semantic-kernel, run-llama/llama_index, pydantic-ai, deepset-ai/haystack,
NVIDIA-NeMo/NeMo-Guardrails, ag2ai/ag2, microsoft/presidio, browser-use/browser-use,
griptape-ai/griptape.

Twenty-two clean, fourteen with findings.

## 3. Absent from CWE

CWE-693, Protection Mechanism Failure, is the correct parent. Its extended
description covers "ignored mechanisms where available protections aren't
applied in certain code paths," which is close, but that is prose in a parent
entry rather than a classified weakness.

None of CWE-693's 18 child weaknesses describes a protection mechanism that
executes, reports success, and never evaluates its comparison. The children
cover missing encryption, weak encryption, broken algorithms, insufficient
randomness, client-side enforcement, single-factor reliance, and similar.

CWE-1288, Improper Validation of Consistency within Input, is the nearest
non-child and does not fit: it concerns consistency between input elements, not
a comparison that fails to evaluate.

Checked against CWE 4.20.

## 4. Absent from the agentic taxonomies

AVE (Agentic Vulnerability Enumeration) maintains 81 behavioral classes for
agentic AI components. Searching its records for `fail-open`, `fails open`,
`enforcement`, `guard` and `silently` returns zero matches in all five cases.

The Cloud Security Alliance's March 2026 agentic catalog names the CWE gaps it
considers most important: goal misalignment, behavioral drift, memory
poisoning, and delegation-chain privilege escalation. This class is not among
them.

## What the four measurements together support

That this is a defect of young enforcement code specifically, not of software
generally. It is reviewed out of mature codebases, and it is concentrated in
systems whose enforcement layers were written quickly, recently, and often not
by security engineers.

And that it currently has no identifier. A maintainer who wants to say "that is
an instance of X, here is the standard mitigation" has no X to point at, and a
scanner vendor who wants to detect it has nothing to map a rule to.

## What they do not support

That the class is dangerous in every instance. Several of the fourteen require
a specific configuration, and two are in sample code rather than shipped
libraries.

That the 36-project sample is representative. It was selected for having
enforcement code worth reading, not at random, so the 14-in-36 rate is an
observation about a chosen sample and not a population estimate.

That the detector in measurement 1 would have found all fourteen. It would
not. It detects one shape of several, which is why the young-code findings
came from reading. The zero in measurement 1 bounds that one shape only.

That every finding was actionable. Two of the fourteen are in code with no
live disclosure path: one maintainer has already declared the affected
directory unsupported, and one project has been archived with no security
policy. Both demonstrate the pattern; neither represents a live risk anyone
is going to patch.

## Reproducing the measurements

Measurements 3 and 4 are checkable in a browser in about ten minutes:
cwe.mitre.org/data/definitions/693.html for the child list, and the `records/`
directory of github.com/aveproject/ave for the 81 classes.

Measurement 2 is this repository plus the clean list above.

Measurement 1 is the one requiring trust, because the detector is not published
here. It found nothing, which is the least interesting possible result to
publish, and a tool with no demonstrated yield is not worth anyone installing.
The number is stated so the claim in measurement 2 has a denominator, not as a
product announcement.
