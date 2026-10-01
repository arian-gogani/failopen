# failopen

Guardrails, policy gates and eval scorers that return the safe answer without
checking anything. Active cases are reproductions of identified source
revisions, not a guarantee that a later upstream revision remains affected.
Withdrawn or superseded claims remain visible under [historical/](historical/).

**Correction, October 1, 2026:** The AutoGen governance sample case was
presented as a current fail-open even though the contributor had already
hardened PR #7960 on September 14, before issue #8301 was filed. The initial
PR revision does execute on unrecognized verdicts; the current PR head
blocks them. The [version comparison](historical/autogen-verdict/README.md)
records both results. AutoGen is removed from the active case list. The
original 15-in-36 audit tally is withdrawn as a measure of current defects.
We also rechecked deepeval: its three affected schemas now reject verbose
verdicts, so that case is [historical](historical/deepeval/README.md) too.
The other projects' present-day statuses have not all been rechecked.

```
git clone https://github.com/arian-gogani/failopen
cd failopen
python3 run.py openai-approval
```

```
lifted evaluate_needs_approval_setting verbatim from the shipped file

  needs_approval           core runner              realtime session
  'always'                 raises UserError         needs_approval=False
```

The helper is extracted from OpenAI Agents' current source. The core runner
uses strict validation; the realtime caller passes `strict=False`, so a
misconfigured approval setting becomes no approval in that path.

No dependencies. Python 3.9 or later.

## The cases

| case | product | what breaks |
|---|---|---|
| `openai-approval` | openai/openai-agents-python | a bad approval config raises in one runner and skips approval in the other |
| `litellm-aporia` | BerriAI/litellm | the provider says `modify`, the proxy forwards the original unmodified |
| `guardrails-onfail` | guardrails-ai | the config path defaults to doing nothing, the Python API defaults to raising |
| `autogpt-server-noperm` | Significant-Gravitas/AutoGPT | the network-facing server builds an agent with no permission manager, and the check silently skips |
| `rebuff-llm-tactic` | protectai/rebuff | an unparseable model completion silently scores as not-detected |

```
python3 run.py --all
```

`openai-approval` fetches the real source file and executes the helper, so it
needs network. The other active cases reproduce the branch structure offline.

## The shape

The cases illustrate one defect family. Something compares a value
it does not control against a literal, and the branch for "did not match" is
the permissive one.

```python
if verdict == "deny":
    return blocked
return allowed          # everything else: "denied", "DENY", "", None
```

Refusal requires an exact match. Permission requires nothing.

It survives review because the code reads correctly, and you have to already be
asking what else the value can be. It survives tests because the tests are
written from the same understanding as the code. It survives coverage because
the guard executes, so the line is covered by inputs that never exercise the
comparison in the direction that matters. Type annotations do not stop it: the
value arrives from `json.loads` or from a model, so `Literal["allow","deny"]`
documents an intent nothing enforces at runtime.

## How common is it

Four measurements, in [MEASUREMENT.md](MEASUREMENT.md), with the limits of each
stated:

- **0 findings in 1,128,865 lines** of mature reviewed Python (certbot, bandit,
  pyjwt, sigstore-python, python-tuf, detect-secrets)
- **The original 15-in-36 tally is withdrawn as a current-defect rate.** It
  included a historical AutoGen PR revision fixed before the public issue and
  a deepeval revision superseded by stricter verdict schemas.
  See [MEASUREMENT.md](MEASUREMENT.md) for the sampling limits.
- **absent from CWE**: none of CWE-693's 18 child weaknesses describes a
  mechanism that executes, reports success, and never evaluates
- **absent from the agentic taxonomies**: zero matches across AVE's 81
  behavioral classes, and not among the four gaps CSA named in March 2026

These selected observations do not establish a population rate or prove the
class is specific to young code. The taxonomy question is separate from that
prevalence claim.

## Checking your own code

```
python3 detector/vacuous.py path/to/your/code
```

[detector/](detector/) finds security verdicts computed by `all()` or `any()`
over a collection that can be empty, because `all([])` is `True` and a
verdict aggregated that way reports success having inspected nothing.

It covers one of the five forms below, the only one with no existing CWE
entry and the only one a static pass decides well. It reports EMPTIABLE and
INDETERMINATE as separate classes and will not merge them, because calling an
undecided question a pass is the defect this repository is about.

Measured against 1,868 files of the Python 3.14 standard library: zero
emptiable, eight indeterminate. It reports both real sites of the llm-guard
finding. Limits, including the two false positives found and fixed while
building it, are in [detector/README.md](detector/README.md).

## Giving it an identifier

[CWE-PROPOSAL.md](CWE-PROPOSAL.md) is a draft entry for this class, written
for discussion in the CWE AI Working Group rather than submitted. It lists
the five structural forms the confirmed instances take, the boundary against
CWE-697 and CWE-184, what static analysis can and cannot detect, and the
part that is currently weakest: there is one credited advisory to cite, and
four instances were filed as public issues before I understood that this
forfeits the credited-instance trail such an entry wants.

## Where it is not

Twenty-one repositories were read and found clean. They are listed because a
sweep that finds a defect everywhere it looks is measuring the sweeper.

langchain, langgraph, crewAI, letta-code, braintrust autoevals, Arize phoenix,
comet opik, langfuse, the MCP filesystem server, the MCP Python SDK, mcp-agent,
block/goose, NVIDIA SkillSpector, microsoft/semantic-kernel, run-llama/llama_index,
pydantic-ai, deepset-ai/haystack, ag2ai/ag2,
microsoft/presidio, browser-use/browser-use, griptape-ai/griptape.

Three of those parse LLM judge output, which is deepeval's exact job. Opik has
one strict parser shared by all ten of its metrics. Autoevals constrains the
model with a tool call and subscripts the result directly, so an unrecognised
choice is a `KeyError`. Phoenix tests membership before scoring and raises.

Deepeval's current `role_violation`, `prompt_alignment`, and
`conversation_completeness` verdict schemas all use the bounded `YesNo` type.
We executed those schema classes and confirmed they reject a verbose verdict.
The older case and the correction are preserved under [historical/deepeval/](historical/deepeval/).

So this is not a claim that LLM tooling is careless. Most of it gets this right.

## Reporting

Every case but two was reported upstream before it was published, through the
project's own channel where one exists. Six further findings are with
vendors under private disclosure and are not here.

The two exceptions are `autogpt-server-noperm` and `rebuff-llm-tactic`.
AutoGPT's SECURITY.md states that code under `classic/` is explicitly out of
scope for security reports, because that directory is unsupported and
superseded by the AutoGPT Platform. Rebuff has been archived since 2024 and
never had a SECURITY.md. Neither had a channel to report through. Both are
published because they are real, reproduced instances of the pattern, not
because anyone has been notified or is expected to fix them. If you run
`classic/`'s Agent Protocol server, the fix is yours to make: pass a
`CommandPermissionManager` into `create_agent()` at the call site in
`agent_protocol_server.py`, the same way the CLI entry point already does.

## On being wrong

A case that cannot reach a verdict prints INCONCLUSIVE and exits non-zero
rather than claiming a result. That rule exists because an earlier version of
one of these scripts printed REPRODUCED after both of its test cases had
crashed on a missing import, which is the defect this repository is about,
in the code written to demonstrate it.

Four public corrections were already issued on one of these findings, each
because a conclusion was stated at wider scope than the evidence supported.
Corrections here get the same prominence as the original claim. If a case is
wrong, open an issue and it will be marked wrong rather than quietly edited.

MIT.
