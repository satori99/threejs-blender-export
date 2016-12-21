# image.py

from bpy.types import Action
from bpy.path import clean_name

from collections import OrderedDict
from mathutils import Matrix, Quaternion, Vector

from .util import get_uuid
from .math import MAT4_ROT_X_PI2


def export_action(act, exporter=None):
    """exports a Blender action as a dictionary representing a three.js
    AnimationClip instance

    """

    assert isinstance(act, Action), \
        "export_action() expects a `bpy.types.Action instance"

    def _flatten_list(l):
        return [a for b in l for a in b]

    out = OrderedDict()

    out["uuid"] = get_uuid(act)
    out["name"] = act.name
    out["type"] = "AnimationClip"

    fps = exporter.scene.render.fps
    frames = act.frame_range[1] - act.frame_range[0]
    duration = (frames - 1) * (1 / fps)
    print("fps", fps)
    print("frames", frames)
    print("duration", duration)

    out["fps"] = fps
    out["duration"] = duration

    tracks = out["tracks"] = []

    for group in act.groups:

        group_name = clean_name(group.name)
        num_channels = len(group.channels)

        # print("group:", group_name, num_channels)

        ob = exporter._act_map.get(act)
        arm = exporter._arm_map.get(ob)
        bones = exporter._bone_map.get(arm)

        # print("bones:", bones)

        bone = next(b for b in bones if clean_name(b.name) == group_name)

        if bone.parent in bones:
            parent_matrix = bone.parent.matrix_local
            bone_matrix = bone.matrix_local
            bone_matrix = parent_matrix.inverted() * bone_matrix
        else:
            bone_matrix = bone.matrix_local
        pos, rot, scl = bone_matrix.decompose()

        # print("bone quaternion:", rot)

        for data_path in set(c.data_path for c in group.channels):

            path = data_path.rsplit('.', 1)[-1:][0]

            # make sure each channel for this data path is unmuted
            if any(c.mute for c in group.channels
                   if c.data_path == data_path):
                print("%s\t%s has muted channels. skipping ..." % (
                      group_name, path))
                continue

            channels = sorted([c for c in group.channels
                              if c.data_path == data_path],
                              key=lambda c: c.array_index)

            # make sure each channel for this data path has the same keyframes
            channel_keyframe_times = [[p.co.x for p in c.keyframe_points]
                                      for c in channels]

            if any(i != channel_keyframe_times[0]
                   for i in channel_keyframe_times):
                print("%s\t%s has mismatched keyframes. skipping ..." % (
                      group_name, path))
                continue

            track_name = \
                path.replace("rotation_", "").replace("location", "position")

            track = OrderedDict()
            track["name"] = "%s.%s" % (group_name, track_name)
            track["type"] = \
                track_name if track_name == "quaternion" else "vector3"

            times = track["times"] = channel_keyframe_times[0]

            channel_keyframe_values = \
                [[p.co.y for p in c.keyframe_points] for c in channels]

            if track_name == "quaternion":
                values = [Quaternion([i[j]
                          for i in channel_keyframe_values]).normalized()
                          for j in range(len(times))]

                values = [rot * v for v in values]

                track["values"] = _flatten_list(
                    [[v.x, v.z, -v.y, v.w] for v in values])

            elif track_name == "position":
                # print("processing position track ...", pos)
                values = [Vector([i[j]
                          for i in channel_keyframe_values])
                          for j in range(len(times))]

                values = [bone_matrix * v for v in values]

                track["values"] = _flatten_list(
                    [[v.x, v.z, -v.y] for v in values])

            else:

                values = [([i[j] for i in channel_keyframe_values])
                          for j in range(len(times))]

                track["values"] = _flatten_list(values)

            print("-> %s.%s" % (group_name, track_name))

            tracks.append(track)

    return out
