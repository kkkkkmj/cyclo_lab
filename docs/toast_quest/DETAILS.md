# Historical Measurement and Validation References

Use [Changes](../../CHANGES.md) as the single source for current settings, setup, and commands.
The reports below preserve settings and results from their respective runs; they are not current execution guidance.

| Reference | Scope |
|---|---|
| [Baseline comparison](BASELINE.md) | Fixed baseline commit, changes by area, preservation of existing READMEs |
| [Validation record](VALIDATION.json) | CPU/file-extraction/regeneration results before document consolidation |
| [Rack diagnostics](https://github.com/kkkkkmj/cyclo_lab/blob/a18eb900aea6d6110dedb45f3f616411f7750c42/scenario_delivery/v20261108_current_100/rack_diagnosis_20261109/README.md) | Approximately 18.5 mm settling; cooked contact unconfirmed |
| [Rack replacement record](history/BREAD_SLOT.md) | Geometry/initial poses/historical static assessment |
| [Gain record](history/GRIPPER_GAINS.md) / [velocity record](history/GRIPPER_SPEED.md) | Comparison values 2/0.5 and 100/4, master-limit changes, CPU/readback limitations |
| [Quest development record](history/QUEST.md) | Historical HUD/input/recording/replay/response experiments |
| [LED record](history/TOASTER_LED.md) / [success-criteria record](history/TOAST_SUCCESS.md) | Incremental logic changes and tests at that time |

Code, host paths, and personal log locations under history are retained as historical records, not a list of files to copy
for current shared execution. Read historical gain descriptions alongside the correction in the [fixed-baseline comparison](BASELINE.md).
CPU checks, historical +15 mm PhysX measurements, and the unverified current +35 mm/VR status remain distinct.

See [Changes](../../CHANGES.md#③-current-settings-and-task-success-criteria) for the current rising-target change from +15 → +35 mm.
Personal measurement originals and tools were moved to local backup and are not shared-execution dependencies.
