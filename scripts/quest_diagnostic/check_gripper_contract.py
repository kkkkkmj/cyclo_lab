"""CPU action/recorder/loader contract. Synthetic fixture, NOT a simulated demonstration."""
import argparse,ast,importlib.util,json,sys
from pathlib import Path
from types import SimpleNamespace as NS
import torch
from control import BoundedTeleop
from diagnostic_recorder import DiagnosticRecorder
from test_control import sample,POSES
ROOT=Path(__file__).resolve().parents[2]


def actual_method(path,name):
    tree=ast.parse(path.read_text());method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
    scope={'torch':torch};exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),str(path),'exec'),scope)
    return scope[name]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    folder=ROOT/'third_party/IsaacLab/source/isaaclab/isaaclab/utils/datasets'
    spec=importlib.util.spec_from_file_location('_actual_dataset_contract',folder/'__init__.py',submodule_search_locations=[str(folder)])
    datasets=importlib.util.module_from_spec(spec);sys.modules[spec.name]=datasets;spec.loader.exec_module(datasets)
    handler=datasets.HDF5DatasetFileHandler();handler.create(str(a.output/'dataset.hdf5'),'CPU_CONTRACT_NOT_SIMULATION')
    ep=datasets.EpisodeData()
    manager=NS(_dataset_file_handler=handler,cfg=NS(export_in_record_pre_reset=False),get_episode=lambda _:ep,reset=lambda _:None)
    manager.export_episodes=lambda ids=None:handler.write_episode(ep)
    manager.record_pre_reset=lambda *a,**k:manager.export_episodes([0])
    env=NS(recorder_manager=manager,termination_manager=NS(active_terms=[]))
    rec=DiagnosticRecorder(env,dict(kind='cpu_action_contract_not_demonstration',operator='fixture',scenario_id='CPU_ONLY',manifest_sha256='NONE',seed=1))
    rec.start(1,{},1);c=BoundedTeleop(POSES,1,True);s=sample();c.update(s)
    for h in s['packet']['controllers'].values():h['buttons'][1]['value']=1
    c.update(s);expected=[]
    for i in range(21):
        left,right=s['packet']['controllers']['left'],s['packet']['controllers']['right']
        left['buttons'][0]['value']=i/20;right['buttons'][0]['value']=1-i/20
        left['position'][2]-=.002;right['position'][2]-=.001
        c.update(s);action=torch.tensor(c.action(POSES,.04));expected.append(action)
        ep.add('actions',action);ep.add('obs/fixture',torch.zeros(1));ep.add('states/fixture',torch.zeros(1))
    ep.pre_export();rec.finish('cpu_contract');rec.close()
    reader=datasets.HDF5DatasetFileHandler();reader.open(str(a.output/'dataset.hdf5'))
    loaded=reader.load_episode('demo_0','cpu')
    config=ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2'
    split=actual_method(config/'bimanual_env.py','actions_to_gripper_actions')
    process=actual_method(config/'gripper_action.py','process_actions')
    for action in expected:
        got=loaded.get_next_action();torch.testing.assert_close(got,action,atol=0,rtol=0)
        assert got.shape==(15,)
        commands=split(None,got.unsqueeze(0))
        for side,index in [('left',12),('right',13)]:
            torch.testing.assert_close(commands[side].reshape(()),got[index],atol=0,rtol=0)
            obj=NS(_raw_actions=torch.zeros(1,1),_processed_actions=torch.zeros(1,4),_open_command=torch.zeros(1,4),_close_command=torch.full((1,4),1.1))
            process(obj,commands[side]);want=(1-got[index])/2*1.1
            torch.testing.assert_close(obj._processed_actions,torch.full((1,4),float(want)))
    assert loaded.get_next_action() is None;reader.close()
    report=dict(kind='CPU contract; no physics replay',frames=len(expected),action_dim=15,
                left_gripper_range=[-1,1],right_gripper_range=[-1,1],exact_hdf5_loader_roundtrip=True,
                existing_recorder_used=True,actual_task_gripper_methods=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
