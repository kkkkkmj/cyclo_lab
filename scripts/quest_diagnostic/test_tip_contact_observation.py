import ast
import copy
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import tempfile
import json
import numpy as np
from tip_contact_observation import stop_reason
from contact_filter import read_contact
from contact_probe import DiagnosticStop
from summarize_free_gripper import observation_summary


class TipObservationTests(unittest.TestCase):
    def row(self):
        contacts=[]
        for body in ('/r1','/r2','/l1','/l2'):
            other='/l2' if body=='/r2' else '/r2'
            active=body in ('/r2','/l2')
            contacts.append(dict(validation=dict(sensor_paths=[body]),counts=[[int(active)]],net=dict(value=[[0,0,0]]),
                details=[dict(other=other,separation_m=[.0013],normal_force_n=[0.])] if active else []))
        return dict(limit_excess_rad=[0]*4,direct_q={'value':[1.1]*4},wrist_drift_m=0,all_pair_contacts=contacts,
                    contact_pairs=[dict(body='/r2',other='/l2',points=1)])

    def test_only_exact_allowed_pair_within_budgets(self):
        r=self.row();self.assertIsNone(stop_reason(r,['/r2','/l2']))
        r['contact_pairs'][0]['other']='/external/l2'
        self.assertEqual(stop_reason(r,['/r2','/l2']),'unexpected_contact_pair')
        r=self.row();r['all_pair_contacts'][1]['details'][0]['separation_m']=[-.0006]
        self.assertEqual(stop_reason(r,['/r2','/l2']),'tip_penetration_budget_exceeded')
        r=self.row();r['all_pair_contacts'][1]['details'][0]['normal_force_n']=[10.1]
        self.assertEqual(stop_reason(r,['/r2','/l2']),'tip_force_budget_exceeded')
        r=self.row();r['limit_excess_rad'][0]=.011
        self.assertEqual(stop_reason(r,['/r2','/l2']),'joint_limit_excess')
        r=self.row();r['wrist_drift_m']=.006
        self.assertEqual(stop_reason(r,['/r2','/l2']),'wrist_drift')
        r=self.row();r['direct_q']['value'][0]-=.06
        self.assertEqual(stop_reason(r,['/r2','/l2']),'finger_asymmetry_budget_exceeded')

    def test_missing_or_unattributed_measurement_stops(self):
        r=self.row();r['all_pair_contacts'][1]['details']=None
        self.assertEqual(stop_reason(r,['/r2','/l2']),'detailed_contact_measurement_invalid')
        r=self.row();r['all_pair_contacts'][0]['net']['value']=[[1,0,0]]
        self.assertEqual(stop_reason(r,['/r2','/l2']),'unattributed_net_contact')
        r=self.row();r['all_pair_contacts'][1]['counts']=[[2]]
        self.assertEqual(stop_reason(r,['/r2','/l2']),'detailed_contact_measurement_invalid')

    def test_populated_contact_slots_only_and_signed_separation(self):
        v=NS(sensor_count=1,filter_count=1,sensor_paths=['/r2'],filter_paths=[['/l2']],max_contact_data_count=8,check=lambda:True)
        v.get_net_contact_forces=lambda dt:np.zeros((1,3))
        v.get_contact_force_matrix=lambda dt:np.zeros((1,1,3))
        data=[np.full((8,w),np.nan) for w in (1,3,3,1)]
        for x in data:x[3]=0
        data[0][3]=2.;data[3][3]=-.0002
        data.extend([np.array([[1]]),np.array([[3]])]);v.get_contact_data=lambda dt:data
        r=read_contact(v,dict(body='/r2',filters=['/l2']),.01,NS(reason=None,errors=[]),details=True)
        self.assertIsNotNone(r['validation']);self.assertEqual(r['details'][0]['separation_m'],[-.0002])
        self.assertEqual(r['details'][0]['normal_force_n'],[2.])
        data[4][0,0]=8;data[5][0,0]=0
        self.assertIsNone(read_contact(v,dict(body='/r2',filters=['/l2']),.01,NS(reason=None,errors=[]),details=True)['validation'])

    def test_actual_probe_wrapper_preserves_diagnostic_reason(self):
        tree=ast.parse(Path(__file__).with_name('contact_probe.py').read_text())
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='update')
        for error,event in [(DiagnosticStop('contact_detected_free_motion_segment_ended'),'automatic_stop'),(ValueError('broken backend'),'sample_error')]:
            rows=[]
            def fail():raise error
            obj=NS(original=lambda:None,context={},last_counter=0,substep=0,total=0,latest=None,
                   sample=fail,emit=rows.append,stop_on_excess=.01)
            scope=dict(self=obj,env=NS(_sim_step_counter=1),DiagnosticStop=DiagnosticStop)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'actual_probe_wrapper','exec'),scope)
            with self.assertRaises(DiagnosticStop) as raised:scope['update']()
            self.assertEqual(rows[0]['event'],event)
            if event=='automatic_stop':self.assertIs(raised.exception,error)
            else:self.assertEqual(str(raised.exception),'diagnostic_sample_error')

    def test_summary_distinguishes_missing_details_from_zero_force(self):
        r=self.row();r.update(event='physics',context=dict(episode_number=1,phase='closed_hold'),simulation_time_s=3.5,
            direct_velocity=dict(value=[0]*4),symmetry=dict(tip_centers_wrist_m=[[0,.001,0],[0,-.001,0]],tip_projected_gap_m=.001))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'outcome.json').write_text(json.dumps(dict(status='completed',reason='fixture')))
            (p/'contact.jsonl').write_text(json.dumps(r)+'\n')
            result=observation_summary(p)
            self.assertEqual(result['contact_samples'],1)
            self.assertEqual(result['max_pair_normal_force_sum_n'],0)
            self.assertAlmostEqual(result['min_reported_contact_separation_m'],.0013)
            self.assertIsNone(result['process']['process_exit_clean'])
            for c in r['all_pair_contacts']:c['details']=None
            (p/'contact.jsonl').write_text(json.dumps(r)+'\n')
            result=observation_summary(p)
            self.assertIsNone(result['max_pair_normal_force_sum_n'])
            self.assertIsNone(result['min_reported_contact_separation_m'])


if __name__=='__main__':unittest.main()
