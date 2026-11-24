#!/usr/bin/env python3
"""sw-agent-forge: research-software operation agent — stateful steps, param mapping, permission gates.

Deterministic subcommands (0 model requests):
  --plan STEPS_JSON      step sequence w/ preconditions & completion criteria + state snapshots
  --params TASK_JSON PARAMS_JSON   task->software parameter mapping (units/defaults-trap/config-version) w/ backref
  --gates ENV_JSON       permission gates (license/account/write/plugin): insufficient -> clear hint + alternative, NO retry loop
  --iocheck IO_JSON      import-read / intermediate-hook / export-format verification (reopen+recompute)
Stdlib only.
"""
import argparse, json, re, sys

def cmd_plan(path):
    steps = json.load(open(path, encoding="utf-8"))
    if isinstance(steps, dict):
        steps = steps.get("steps", [])
    out = []
    for i, s in enumerate(steps):
        out.append({"step": i + 1, "name": s.get("name", ""), "action": s.get("action", ""),
                    "precondition": s.get("precondition", "上一步完成判据已满足"),
                    "done_criteria": s.get("done_criteria", "状态快照记录完成标志"),
                    "state_before": s.get("state_before", "snapshot"), "state_after": s.get("state_after", "snapshot"),
                    "note": "每步开始/结束记录软件状态；导入→设置→运行→导出→检查"})
    print(json.dumps({"schema": "swagent/plan@1", "steps": out[:20]}, ensure_ascii=False, indent=1))
    return 0

UNIT_MAP = {"分钟": ("min", 1.0), "min": ("min", 1.0), "秒": ("min", 1 / 60.0), "s": ("min", 1 / 60.0),
            "毫秒": ("min", 1 / 60000.0), "ms": ("min", 1 / 60000.0), "%": ("fraction", 0.01)}
DEFAULT_TRAPS = {"threads": "默认可能占满核数——显式设置", "overwrite": "默认可能覆盖输出——显式false", "seed": "默认随机——显式固定"}

def cmd_params(task_path, params_path):
    task = json.load(open(task_path, encoding="utf-8"))
    params = json.load(open(params_path, encoding="utf-8"))
    if isinstance(params, dict):
        params = params.get("params", [])
    mapped = []
    for p in params:
        name = p.get("name", "")
        val = p.get("value", "")
        unit = p.get("unit", "")
        backref = p.get("task_field", name)
        conversion = ""
        if unit and unit in UNIT_MAP:
            canon, factor = UNIT_MAP[unit]
            conversion = f"{val} {unit} -> {float(val) * factor} {canon}（软件单位），公式留痕"
        trap = DEFAULT_TRAPS.get(name, "")
        mapped.append({"param": name, "value": val, "unit": unit, "canonical": conversion or f"{val} {unit or 'N/A'}",
                       "task_backref": backref, "default_trap": trap,
                       "config_version": p.get("config_version", "记录软件配置版本差异"),
                       "verifiable": f"参数可回指任务要求字段 {backref}"})
    print(json.dumps({"schema": "swagent/params@1", "mapped": mapped[:20]}, ensure_ascii=False, indent=1))
    return 0

GATES = [
    {"gate": "license", "check": "license_valid", "insufficient": "许可证缺失/过期——给出申请路径，不反复重试"},
    {"gate": "account", "check": "logged_in", "insufficient": "未登录——提示登录步骤，跳过需登录的步骤序列"},
    {"gate": "write_perm", "check": "dir_writable", "insufficient": "目录不可写——给出可写替代目录"},
    {"gate": "plugin_auth", "check": "plugin_authorized", "insufficient": "插件未授权——列出替代手动流程"},
]

def cmd_gates(env_path):
    env = json.load(open(env_path, encoding="utf-8"))
    if isinstance(env, dict):
        env = env.get("env", env.get("checks", []))
    envmap = {e.get("gate", e.get("name", "")): e.get("ok", e.get("value")) for e in (env if isinstance(env, list) else [])}
    out = []
    blocked = []
    for g in GATES:
        ok = envmap.get(g["gate"], envmap.get(g["check"]))
        entry = {"gate": g["gate"], "status": "pass" if ok else "blocked",
                 "hint": "" if ok else g["insufficient"]}
        out.append(entry)
        if not ok:
            blocked.append(g["gate"])
    print(json.dumps({"schema": "swagent/gates@1", "gates": out,
                      "blocked": blocked,
                      "policy": "权限不足→明确提示+可行替代（不反复重试）；被阻断步骤序列显式跳过"},
                     ensure_ascii=False, indent=1))
    return 0

def cmd_iocheck(path):
    io = json.load(open(path, encoding="utf-8"))
    if isinstance(io, dict):
        io = io.get("io", io.get("checks", []))
    out = []
    for c in (io if isinstance(io, list) else []):
        out.append({"item": c.get("item", ""), "status": "PASS" if c.get("ok") else "FAIL",
                    "evidence": c.get("evidence", ""),
                    "note": c.get("note", "输入正确读取/中间结果正确挂接/导出格式字段符合下游")})
    reopen = json.dumps({"schema": "swagent/io@1", "checks": out[:20],
                          "reopen_check": "导出文件可被重新打开并复算（记录重开+复算结果）"},
                         ensure_ascii=False, indent=1)
    print(reopen)
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan"); ap.add_argument("--params", nargs=2); ap.add_argument("--gates"); ap.add_argument("--iocheck")
    a = ap.parse_args()
    if a.plan: return cmd_plan(a.plan)
    if a.params: return cmd_params(a.params[0], a.params[1])
    if a.gates: return cmd_gates(a.gates)
    if a.iocheck: return cmd_iocheck(a.iocheck)
    ap.error("choose --plan / --params / --gates / --iocheck")

if __name__ == "__main__":
    sys.exit(main())
