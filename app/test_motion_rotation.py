import copy,unittest
import motion_specs as schema


class RotationSafetyTests(unittest.TestCase):
    def example(self):
        ctx=dict(request='demo',texts=['Chữ tiếng Việt'],frames=90,anchors=[dict(id='speech',kind='speech',frame=0)],protected=[])
        spec=schema.rules(ctx);spec.update(scene_type='focus',layout='host');spec['objects']=spec['objects'][:1]
        obj=spec['objects'][0];obj.update(rect=[.25,.55,.5,.07],font_size=38,exit_frames=0,hold_frames=30)
        obj['keyframes']=[dict(frame=0,x=0,y=0,scale=1,opacity=1,ease='linear'),dict(frame=10,x=0,y=0,scale=1,opacity=1,ease='linear')]
        return ctx,spec
    def test_legacy_keys_default_to_zero_rotation(self):
        c,s=self.example();schema.validate(s,c)
        self.assertEqual(schema.pose(s['objects'][0]['keyframes'],5)['rotation'],0)
    def test_rotation_interpolates_and_finishes_readable(self):
        c,s=self.example();keys=s['objects'][0]['keyframes'];keys[0]['rotation']=20
        self.assertEqual(schema.pose(keys,5)['rotation'],10);schema.validate(s,c)
        keys[-1]['rotation']=1
        with self.assertRaisesRegex(ValueError,'settled'):schema.validate(s,c)
    def test_rotated_corner_cannot_enter_protected_face(self):
        c,s=self.example();c['protected']=[dict(kind='face',rect=[.2,.45,.6,.08])];schema.validate(s,c)
        s['objects'][0]['keyframes'][0]['rotation']=45
        with self.assertRaisesRegex(ValueError,'protected face'):schema.validate(s,c)
    def test_contact_marker_cannot_rotate_away_from_real_target(self):
        c=dict(request='demo',texts=[],frames=90,protected=[],proof=dict(data_class='real_screen'),anchors=[dict(id='tap',kind='contact',frame=0,roi=[.2,.4,.05,.03])]);s=schema.rules(c)
        s['objects'][0]['keyframes'][0]['rotation']=4
        with self.assertRaisesRegex(ValueError,'stay on'):schema.validate(s,c)
