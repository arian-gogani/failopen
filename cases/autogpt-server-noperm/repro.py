"""Significant-Gravitas/AutoGPT: the network-facing server path builds an
agent with no permission_manager, and the enforcement code treats that as
"nothing to check" instead of "deny by default".

Source, structurally verbatim from the shipped files:
  classic/original_autogpt/autogpt/app/agent_protocol_server.py, create_task()
  classic/original_autogpt/autogpt/agents/agent.py, Agent.execute()

create_task() is the handler behind AutoGPT's Agent Protocol server
(`autogpt serve`, binds 0.0.0.0). It calls create_agent() without a
permission_manager argument, which defaults to None. Agent.execute() only
checks permissions "if self.permission_manager:" -- when that's None, the
whole approval block is skipped, and every tool call reaches execution with
no deny-list, no human approval, nothing. The CLI entry point in the same
codebase (app/main.py) always constructs a CommandPermissionManager and
passes it in, so the same agent class behaves correctly there. Only the
server path drops it.

Not reported: AutoGPT's SECURITY.md lists code under classic/ as explicitly
out of scope ("unsupported... avoid use of deprecated components"). This
case exists to document the pattern in a widely cloned codebase, not as an
open disclosure -- the maintainers have already said they will not take
reports against this directory.

https://github.com/Significant-Gravitas/AutoGPT/blob/master/classic/original_autogpt/autogpt/app/agent_protocol_server.py
https://github.com/Significant-Gravitas/AutoGPT/blob/master/classic/original_autogpt/autogpt/agents/agent.py
"""

TITLE = "AutoGPT classic: the server path builds an agent with no permission_manager, and the check silently skips"
UPSTREAM = "not reported -- classic/ is explicit out-of-scope in AutoGPT's own SECURITY.md"


class PermissionDenied(Exception):
    pass


class CommandPermissionManager:
    """A minimal stand-in with the one method Agent.execute() calls."""

    def __init__(self, denylist):
        self.denylist = denylist

    def check_command(self, name, arguments):
        allowed = name not in self.denylist
        return type("Result", (), {"allowed": allowed, "feedback": None})()


def execute(permission_manager, tool_names):
    """Agent.execute(), lines 384-401, structurally verbatim.

    Real signature takes an ActionProposal and returns an ActionResult; this
    keeps only the branch that matters, tool names in and a verdict out.
    """
    if permission_manager:
        for name in tool_names:
            perm_result = permission_manager.check_command(name, {})
            if not perm_result.allowed:
                return "BLOCKED: %s" % name
    return "EXECUTED: %s" % ", ".join(tool_names)


def create_agent_cli_path(permission_manager):
    """app/main.py: both CLI branches construct and pass a manager."""
    return execute(permission_manager, ["execute_shell", "write_file"])


def create_agent_server_path():
    """agent_protocol_server.py create_task(): no permission_manager kwarg,
    so Agent.__init__ default (None) is what Agent.execute() sees."""
    return execute(None, ["execute_shell", "write_file"])


def run():
    print("Same denylist, two entry points into the same Agent class:\n")

    manager = CommandPermissionManager(denylist={"execute_shell"})

    cli_result = create_agent_cli_path(manager)
    print("  CLI entry point   (app/main.py, manager passed)    -> %s" % cli_result)

    server_result = create_agent_server_path()
    print("  Server entry point (create_task, manager omitted)  -> %s" % server_result)

    print()
    cli_blocked = cli_result.startswith("BLOCKED")
    server_blocked = server_result.startswith("BLOCKED")

    if cli_blocked and not server_blocked:
        print("The CLI path blocks execute_shell. The server path, reachable")
        print("over HTTP via POST /ap/v1/agent/tasks, runs it. Same denylist,")
        print("same Agent class, same tool call. The only difference is whether")
        print("the caller remembered to construct a CommandPermissionManager.")
        return True
    print("No divergence. The defect did not reproduce.")
    return False
