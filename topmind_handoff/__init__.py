"""Local, deterministic memory compiler for topmind-handoff.

Views are a pure function of per-origin outboxes, authority, and environment
cards. Nothing in this package talks to the network.
"""

from topmind_handoff.compile import (
    compile_ops,
    compile_repo,
    next_op_id,
    record_retract,
    record_resolve,
    record_set,
    record_work,
    save_environment_card,
    startup_read,
    status_is_valid,
)
from topmind_handoff.admin import init_memory_repo, organize_repo, set_scenario_owner
from topmind_handoff.package import (
    HostMergePlan,
    apply_host_merge,
    plan_host_merge,
    render_package,
    replay_package,
)

__all__ = [
    "HostMergePlan",
    "apply_host_merge",
    "compile_ops",
    "compile_repo",
    "init_memory_repo",
    "next_op_id",
    "organize_repo",
    "plan_host_merge",
    "record_retract",
    "record_resolve",
    "record_set",
    "record_work",
    "render_package",
    "replay_package",
    "save_environment_card",
    "set_scenario_owner",
    "startup_read",
    "status_is_valid",
]
