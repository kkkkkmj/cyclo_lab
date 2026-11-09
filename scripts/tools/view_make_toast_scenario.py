"""View one fixed toast layout. R resets it; closing the window exits.

No expert, recording, asset download, or diagnostic object disturbance.
Use --steps and --reset_every for a finite headless smoke check.
"""
import argparse
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSIGNMENTS = ROOT / "scenario_delivery/assignments.csv"


GROUPS = ("operator_A_1", "operator_A_2", "operator_B_1", "operator_B_2")


def add_group_arguments(parser):
    parser.add_argument("--scenario_group", choices=GROUPS, help="Versioned delivery subgroup")
    parser.add_argument("--group_index", type=int, help="1-based subgroup position (1–25)")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario_id", help="Omit all selection arguments for the original layout")
    parser.add_argument("--operator", choices=("operator_A", "operator_B"))
    parser.add_argument("--scenario_index", type=int, help="1-based position in this operator's CSV list (1–50)")
    parser.add_argument("--scenario_manifest", help="Defaults to scenario_delivery/manifest.json")
    parser.add_argument("--steps", type=int, default=0, help="Exit after N steps; 0 keeps viewing")
    parser.add_argument("--reset_every", type=int, default=0, help="Reset every N steps; 0 disables")
    add_group_arguments(parser)
    return parser


def resolve_selection(args, assignments_path=None):
    """Resolve legacy operator or versioned subgroup selection before simulation.

    For groups, populate operator/scenario_index for the existing recorder API.
    Old manifests retain the old assignment CSV; versioned ones name a sibling CSV.
    """
    group = getattr(args, "scenario_group", None)
    group_index = getattr(args, "group_index", None)
    grouped = group is not None or group_index is not None
    paired = args.operator is not None or args.scenario_index is not None
    already = getattr(args, "_resolved_scenario_group", False)
    if grouped and (group not in GROUPS or group_index is None or not 1 <= group_index <= 25):
        raise ValueError("Supply --scenario_group and --group_index 1–25 together")
    if grouped and ((paired and not already) or args.scenario_id is not None):
        raise ValueError("Group selection cannot combine with operator/index or scenario_id")
    if not grouped and paired and args.scenario_id is not None:
        raise ValueError("Use either --scenario_id or --operator with --scenario_index, not both")
    if not grouped and paired and (args.operator is None or args.scenario_index is None):
        raise ValueError("--operator and --scenario_index must be supplied together")
    if not grouped and not paired and args.scenario_id is None:
        return None
    if not grouped and paired and (args.operator not in ("operator_A", "operator_B") or not 1 <= args.scenario_index <= 50):
        raise ValueError("Expected operator_A/operator_B and --scenario_index in 1–50")
    path = ROOT / "source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/scenarios.py"
    spec = importlib.util.spec_from_file_location("toast_viewer_loader", path)
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    data = loader.load_manifest(args.scenario_manifest)
    entries = {entry["id"]: entry for entry in data["scenarios"]}
    ids = set(entries)
    if not paired and not grouped:
        if args.scenario_id not in ids:
            raise ValueError(f"Unknown scenario ID {args.scenario_id!r}")
        return args.scenario_id
    csv_path = ASSIGNMENTS
    if "assignments_file" in data:
        if data["assignments_file"] != "assignments.csv":
            raise ValueError("Versioned delivery must use sibling assignments.csv")
        csv_path = Path(args.scenario_manifest or loader.MANIFEST).resolve().parent / "assignments.csv"
    with Path(assignments_path or csv_path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"scenario_id", "operator", "order_positive_to_negative_y"} <= set(reader.fieldnames or ()):
            raise ValueError("Assignment CSV is missing required columns")
        rows = list(reader)
    seen = set()
    for row in rows:
        sid = row["scenario_id"]
        if row["operator"] not in ("operator_A", "operator_B"):
            raise ValueError(f"Invalid operator in assignments: {row['operator']!r}")
        if sid in seen or sid not in ids:
            raise ValueError(f"Duplicate or unknown assignment ID: {sid}")
        if entries[sid]["operator"] != row["operator"]:
            raise ValueError("Assignment operator disagrees with manifest")
        seen.add(sid)
    if seen != ids or any(sum(row["operator"] == op for row in rows) != 50 for op in ("operator_A", "operator_B")):
        raise ValueError("Assignments must cover the manifest exactly, 50 per operator")
    if "assignments_file" in data:
        for row in rows:
            g=row.get("scenario_group"); i=int(row.get("group_index",0)); oi=int(row.get("operator_index",0))
            if g not in GROUPS or row['operator'] != g.rsplit('_',1)[0] or not 1<=i<=25 or oi!=i+(25 if g.endswith('_2') else 0):
                raise ValueError("Invalid group/operator index mapping")
            entry=entries[row['scenario_id']]
            if any(str(entry.get(k))!=str(row[k]) for k in ('scenario_group','group_index','operator_index')):
                raise ValueError("Assignment group/index disagrees with manifest")
        for g in GROUPS:
            if sorted(int(r['group_index']) for r in rows if r['scenario_group']==g)!=list(range(1,26)):
                raise ValueError("Each subgroup must contain indices 1–25 exactly once")
        for op in ('operator_A','operator_B'):
            if [int(r['operator_index']) for r in rows if r['operator']==op]!=list(range(1,51)):
                raise ValueError("Versioned CSV must preserve operator index order 1–50")
    if grouped:
        if "assignments_file" not in data:
            raise ValueError("Group selection requires a versioned manifest; specify --scenario_manifest")
        row=next(r for r in rows if r['scenario_group']==group and int(r['group_index'])==group_index)
        args.operator=row['operator'];args.scenario_index=int(row['operator_index'])
        args._resolved_scenario_group=True
        return row['scenario_id']
    assigned = [row["scenario_id"] for row in rows if row["operator"] == args.operator]
    return assigned[args.scenario_index - 1]


def main():
    from isaaclab.app import AppLauncher

    parser = build_parser()
    AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()
    if args.steps < 0 or args.reset_every < 0:
        parser.error("Step counts must be nonnegative")
    try:
        selected_id = resolve_selection(args)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    if args.operator is not None:
        print(f"SCENARIO_SELECTED operator={args.operator} scenario_index={args.scenario_index} scenario_id={selected_id}", flush=True)
    args.scenario_id = selected_id
    args.enable_cameras = True
    app = AppLauncher(args).app
    env = None
    keyboard = subscription = input_interface = None
    try:
        import gymnasium as gym
        import torch
        import cyclo_lab  # noqa: F401 — registers tasks
        from isaaclab_tasks.utils.parse_cfg import parse_env_cfg

        task = "Cyclo-Make-Toast-FFW-BG2-Bimanual-IK-Rel-v2"
        cfg = parse_env_cfg(task, device=args.device, num_envs=1)
        cfg.scenario_id = args.scenario_id
        cfg.scenario_manifest = args.scenario_manifest
        env = gym.make(task, cfg=cfg).unwrapped

        def reset():
            env.reset()
            # Compare immediate initial poses, not subsequent settling or task success.
            for name in ("toaster", "plate", "bread_shelf", *(f"bread_{i}" for i in range(4))):
                if name == "bread_shelf":
                    position, quaternion = env.scene[name].get_world_poses()
                else:
                    state = env.scene[name].data.root_state_w
                    position, quaternion = state[:, :3], state[:, 3:7]
                initial = getattr(env.cfg.scene, name).init_state
                target = torch.tensor([(*initial.pos, *initial.rot)], device=env.device)
                torch.testing.assert_close(position - env.scene.env_origins, target[:, :3], atol=5e-5, rtol=0)
                dot = (quaternion * target[:, 3:]).sum(-1).abs()
                torch.testing.assert_close(dot, torch.ones_like(dot), atol=5e-5, rtol=0)
            print("RESET_POSES_OK", args.scenario_id or "original", flush=True)

        reset()
        reset_requested = False
        if not args.headless:
            import carb.input
            import omni.appwindow
            input_interface = carb.input.acquire_input_interface()
            keyboard = omni.appwindow.get_default_app_window().get_keyboard()

            def on_keyboard(event, *unused):
                nonlocal reset_requested
                if event.type == carb.input.KeyboardEventType.KEY_PRESS and event.input == carb.input.KeyboardInput.R:
                    reset_requested = True
                return True

            subscription = input_interface.subscribe_to_keyboard_events(keyboard, on_keyboard)
        # Match the established layout hold: zero arm deltas, open grippers, lift zero.
        action = torch.zeros((1, 15), device=env.device)
        action[:, 12:] = 1
        step = 0
        with torch.inference_mode():
            while app.is_running() and (args.steps == 0 or step < args.steps):
                if reset_requested or (args.reset_every and step and step % args.reset_every == 0):
                    reset()
                    reset_requested = False
                _, _, terminated, truncated, _ = env.step(action)
                if bool((terminated | truncated).any()):
                    raise RuntimeError("Task automatically reset during viewing; inspect the environment")
                step += 1
        print(f"VIEW_COMPLETE steps={step}", flush=True)
    finally:
        if subscription is not None:
            input_interface.unsubscribe_to_keyboard_events(keyboard, subscription)
        if env is not None:
            env.close()
        app.close()


if __name__ == "__main__":
    main()
