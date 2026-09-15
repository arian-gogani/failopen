# failopen

Guardrails, policy gates and eval scorers that return the safe answer without
checking anything. Every case here is reproduced against the code as shipped,
not described.

```
git clone https://github.com/arian-gogani/failopen
cd failopen
python3 run.py deepeval
```

```
lifted 10 lines of _calculate_score verbatim from the shipped file

  judge verdict                                    score   meaning
  'yes'                                            0.0     violation caught
  'Yes, the model violated its assigned role.'     1.0     scored as full adherence
  'no'                                             1.0     scored as full adherence
```

That is deepeval's own `_calculate_score`, downloaded from `main` and executed.
A judge that answers in a sentence rather than a bare token is scored as
reporting no violation.

No dependencies. Python 3.9 or later.

## The cases

| case | product | what breaks |
|---|---|---|
| `deepeval` | confident-ai/deepeval | a verbose judge verdict scores as a pass, in three metrics |
| `openai-approval` | openai/openai-agents-python | a bad approval config raises in one runner and skips approval in the other |
| `litellm-aporia` | BerriAI/litellm | the provider says `modify`, the proxy forwards the original unmodified |
| `guardrails-onfail` | guardrails-ai | the config path defaults to doing nothing, the Python API defaults to raising |
| `autogen-verdict` | microsoft/autogen | a governance sample executes on any verdict it does not recognise |
| `autogpt-server-noperm` | Significant-Gravitas/AutoGPT | the network-facing server builds an agent with no permission manager, and the check silently skips |

```
python3 run.py --all
```

`deepeval` and `openai-approval` fetch the real source file and execute the
function out of it, so those two need network. The rest reproduce the branch
structure exactly and run offline.

## The shape

All six are one defect wearing different clothes. Something compares a value
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
- **10 findings in 27 projects** whose enforcement code is roughly eighteen
  months old or less
- **absent from CWE**: none of CWE-693's 18 child weaknesses describes a
  mechanism that executes, reports success, and never evaluates
- **absent from the agentic taxonomies**: zero matches across AVE's 81
  behavioral classes, and not among the four gaps CSA named in March 2026

Together those say this is a defect of young enforcement code rather than of
software generally, and that it currently has no identifier for a maintainer to
point at or a scanner to map a rule to.

## Where it is not

Seventeen repositories were read and found clean. They are listed because a
sweep that finds a defect everywhere it looks is measuring the sweeper.

langchain, langgraph, crewAI, letta-code, braintrust autoevals, Arize phoenix,
comet opik, langfuse, the MCP filesystem server, the MCP Python SDK, mcp-agent,
block/goose, NVIDIA SkillSpector, microsoft/semantic-kernel, run-llama/llama_index,
pydantic-ai, deepset-ai/haystack.

Three of those parse LLM judge output, which is deepeval's exact job. Opik has
one strict parser shared by all ten of its metrics. Autoevals constrains the
model with a tool call and subscripts the result directly, so an unrecognised
choice is a `KeyError`. Phoenix tests membership before scoring and raises.

deepeval ships the same helper. `verdict_from_json` in `metrics/utils.py`, with
a docstring naming this exact failure, including the phrase "silently
miscounting it". One metric calls it.

So this is not a claim that LLM tooling is careless. Most of it gets this right.

## Reporting

Every case but one was reported upstream before it was published, through the
project's own channel where one exists. Two further findings are with vendors
under private disclosure and are not here.

The exception is `autogpt-server-noperm`. AutoGPT's SECURITY.md states that
code under `classic/` is explicitly out of scope for security reports,
because that directory is unsupported and superseded by the AutoGPT
Platform. There was no channel to report it through. It is published because
it is a real, reproduced instance of the pattern in a widely cloned
repository, not because anyone has been notified or is expected to fix it.
If you run `classic/`'s Agent Protocol server, the fix is yours to make: pass
a `CommandPermissionManager` into `create_agent()` at the call site in
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
