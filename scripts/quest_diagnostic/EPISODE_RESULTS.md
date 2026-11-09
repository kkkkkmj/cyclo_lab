# Quest episode results

## Serving success

At least one of bread_0–3 must have completed the existing heating qualification and that **same ID**
must meet the plate-placement predicate. The bread geometry center must be less than 20 mm from the
plate-local XY origin; all bread geometry must have local Z greater than −2 mm and less than 50 mm,
with abs(R[2,2]) >0.94 and linear speed <0.15 m/s. The plate must be upright (R[2,2] >0.985), within
25 mm of its initial XY position, and at environment X >0.419 m. The toaster cycle must be complete
(phase 4) and the lever returned.

Neither wrist standby position, either gripper joint1 angle, nor lift return position constrains
serving success. Other bread slices have no shelf-retention requirement. Independent failure terms,
including bread dropping, still terminate an episode. No contact sensor or success dwell time was added.
The non-serving task retains its existing posture checks. Physics, control, reset poses, gains, velocity
limits, input mapping, 90% activation, 4-second heating and +35 mm rising target are unchanged.

## Result display

The existing status area above HEAD has two rows: controller connectivity, then REC / NO REC next to
a separate, larger result. SUCCESS is green; STOPPED, TRACKING STALL, TIMEOUT and BREAD DROPPED identify
other outcomes. Unrecognized termination names are shown explicitly. A completed result is historical
and remains visible in WAITING even if input becomes stale. Recording status and input freshness remain
separate. A blocked X start does not clear the result; an accepted X start does, before the usual reset.
The PC page now displays the same camera tiles and result badge outside VR, after pairing. The badge
sits above the images, not over their centers. Existing camera observations and MP4 pixels are unchanged.

## Capture and storage

The single-environment Quest launcher snapshots termination terms immediately after Isaac Lab's
termination-manager compute, before recorder pre-reset export and automatic reset. Each actual predicate
return is captured during that compute: the pinned manager's get_term cache retains only the last true
term and can retain stale values on nonterminal steps. This hook only
observes the result and returns the original tensor unchanged; it works without recording. The saved
snapshot drives the WAITING result and periodic terminal telemetry. The recorder uses the same snapshot
and policy for HDF5 `success`, `task_success_observed`, embedded episode metadata and `episode.json`.
Raw active terms remain in `termination_terms` for inspection. No reset-state success reevaluation is used.

Isaac Lab combines termination terms with OR; its generic recorder treats any success term as success,
even when another term also fires. The Quest outcome policy makes this explicit:

| Event | Result / success label |
|---|---|
| Explicit manual stop or tracking stall before another physics step | STOPPED / TRACKING STALL; false, even if stale success terms exist |
| Failure (e.g. bread_dropping) with or without success/timeout | Failure reason; false |
| Success, with or without time_out and no failure | SUCCESS; true |
| time_out alone | TIMEOUT; false |
| Other explicit stop/exit | Actual reason; false |

The physics termination tensor is not changed by this labeling policy. Once an episode has finished,
a later stop command in WAITING cannot relabel it. HDF5 and MP4 recording, incomplete-step trimming,
zero-sample sidecars, and WAITING → accepted X → reset behavior remain in place. An observed success
label does not establish demonstration quality or replay fidelity.

## Validation scope

CPU tests execute the actual serving predicates with USD bread geometry, including each heated bread
ID, wrong/unheated IDs, plate constraints, and success with non-standby arms, closed grippers and a
raised lift. Lifecycle tests clear simulated termination state after capture to check reset-safe results,
blocked/accepted starts, simultaneous failure/success/timeout, and recorder label consistency.
Recorder integration tests use the pinned HDF5 implementation and real MP4 encoding/decoding with
synthetic camera frames. HUD tests exercise both eye viewports, common status bounds, PC layout,
REC plus SUCCESS, and stop/result persistence with mocked canvas/WebGL.

These are CPU checks, not PhysX or Quest runtime validation. Headset optical readability and actual
casting crop remain unverified. No running simulation or server was stopped or restarted.
