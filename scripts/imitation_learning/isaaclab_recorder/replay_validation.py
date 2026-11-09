"""Replay selection and vectorized state validation, importable without Isaac Sim."""
import time
import numpy as np


def resolve_episode_indices(names, indices=None, selected_names=None):
    if indices and selected_names:
        raise ValueError('Select episodes by indices OR names')
    if selected_names:
        missing=[name for name in selected_names if name not in names]
        if missing:raise ValueError(f'Unknown episode names: {missing}; available={names}')
        return [names.index(name) for name in selected_names]
    result=list(indices) if indices else list(range(len(names)))
    if any(i<0 or i>=len(names) for i in result):
        raise ValueError(f'Episode list index outside [0,{len(names)-1}]: {result}')
    return result


def compare_states(state_from_dataset, runtime_state, runtime_env_index, progress=None, *, dataset_has_single_env_axis=False, metrics=None):
    """Absolute tolerance 0.01, no relative tolerance. Transfer whole fields, never GPU scalars.

    Preserve the original articulation/rigid_object comparison scope. Extra recorded
    toast_cycle is restored/checked separately by the diagnostic initial-state check.
    Shape/key mismatches and all NaN/Inf values fail. Detailed output is bounded.
    """
    # Only the caller using EpisodeData.get_next_state() may opt into this contract.
    # No generic squeeze, flatten, or implicit broadcasting is used for alignment.
    if metrics is not None:metrics.clear()
    def log(message):
        if progress:progress(message)
    def flatten(tree,prefix):
        result={}
        for key,value in tree.items():
            path=f'{prefix}/{key}'
            if isinstance(value,dict):result.update(flatten(value,path))
            else:result[path]=value
        return result
    def to_cpu(value):
        if hasattr(value,'detach'):return value.detach().cpu().numpy()
        return np.asarray(value)
    started=time.perf_counter();log('compare.cpu_transfer BEGIN')
    saved={};actual={}
    for group in ('articulation','rigid_object'):
        saved.update(flatten(state_from_dataset.get(group,{}),group))
        actual.update(flatten(runtime_state.get(group,{}),group))
    runtime_axis_errors=set()
    if dataset_has_single_env_axis:
        runtime_axis_errors={k for k,v in actual.items()
                             if runtime_env_index!=0 or len(v.shape)<1 or v.shape[0]!=1}
    saved={k:to_cpu(v) for k,v in saved.items()}
    actual={k:to_cpu(v if k in runtime_axis_errors else v[runtime_env_index]) for k,v in actual.items()}
    log(f'compare.cpu_transfer END elapsed_s={time.perf_counter()-started:.6f} fields={len(actual)}')
    started=time.perf_counter();log('compare.numpy BEGIN')
    issues=[];failed=0
    def fail(message):
        nonlocal failed
        failed+=1
        if len(issues)<20:issues.append(message)
    if not saved or not actual:fail('No comparable state fields')
    for path in sorted(set(saved)|set(actual)):
        if metrics is not None:metrics[path]={'max_abs':None,'matched':False}
        if path in runtime_axis_errors:
            fail(f'{path}: expected exactly one runtime environment at index 0');continue
        if path not in saved or path not in actual:
            fail(f'{path}: missing dataset/runtime field');continue
        a,b=saved[path],actual[path]
        if dataset_has_single_env_axis:
            if a.ndim!=b.ndim+1 or a.shape[0]!=1 or a.shape[1:]!=b.shape:
                fail(f'{path}: single-env shape contract failed dataset={a.shape} runtime={b.shape}');continue
            a=a[0]  # Explicitly remove only the known EpisodeData environment axis.
        if a.shape!=b.shape:
            fail(f'{path}: shape mismatch dataset={a.shape} runtime={b.shape}');continue
        finite=np.isfinite(a)&np.isfinite(b)
        if not finite.all():
            fail(f'{path}: NaN/Inf count={np.count_nonzero(~finite)}');continue
        delta=np.abs(a.astype(np.float64)-b.astype(np.float64))
        bad=delta>0.01
        if metrics is not None:metrics[path]={'max_abs':float(delta.max()) if delta.size else 0.,'matched':not bool(bad.any())}
        if bad.any():
            ids=np.flatnonzero(bad)[:8]
            fail(f'{path}: count={np.count_nonzero(bad)} max_abs={delta.max():.9g} '
                 f'flat_indices={ids.tolist()} dataset={a.reshape(-1)[ids].tolist()} runtime={b.reshape(-1)[ids].tolist()}')
    log(f'compare.numpy END elapsed_s={time.perf_counter()-started:.6f} failed_fields={failed}')
    if failed>len(issues):issues.append(f'{failed-len(issues)} additional failed fields omitted')
    return failed==0,'\n'.join(issues)
