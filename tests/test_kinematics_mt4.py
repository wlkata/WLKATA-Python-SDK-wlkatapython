"""MT4 FK / IK, the firmware's motion bookkeeping and the simulator, checked against a real arm.

``tests/data/mt4_hardware_poses.json`` records a real MT4 (firmware
MT4,20240820) driven from home through joint (M21) and coordinate (M20) moves:
fast, linear and door-shaped, absolute and incremental, with axes left out,
past every limit, out of reach, and switching between the two kinds of move
after refused ones. For each command it has what the arm
replied before "ok" and the status it reported once Idle, and it has the
arm's ``$$`` settings. The simulator replays the same commands and has to
stop on the same motor steps, report the same poses and print the same replies.
"""

import json
import pathlib
import re
import time

import pytest

from wlkatapython.simulator import MT4Simulator, RobotState
from wlkatapython.simulator.kinematics import MT4Kinematics, MT4Motion, mt4
from wlkatapython.simulator.simulated_hardware import mirobot_status_line
from wlkatapython.simulator.virtual_serial import MockSerial


pytestmark = pytest.mark.mt4

HARDWARE = json.loads((pathlib.Path(__file__).parent / "data" / "mt4_hardware_poses.json").read_text())
MOVES = HARDWARE["moves"]
HOME = (230.0, 0.0, 255.57, 0.0, 0.0, 0.0)
STATUS = re.compile(
    r"<(\w+),Angle\(ABCDXYZ\):([-\d.,]+),Cartesian coordinate\(XYZ RxRyRz\):([-\d.,]+),"
    r"Pump PWM:\d+,Valve PWM:\d+,Motion_MODE:(\d)>")

# The arm prints three decimals, computed in single precision: its angles are
# whole motor steps and its pose is theirs, but a value right at a rounding
# boundary can print the other last digit.
ANGLE_TOL = 0.0011
POSE_TOL = 0.002


def parse(line):
    """A status line → (state, [J1..J4], [X, Y, Z, Rx, Ry, Rz], mode)."""
    m = STATUS.fullmatch(line)
    a = [float(v) for v in m.group(2).split(",")]   # A, B, C, D, X, Y, Z
    return m.group(1), [a[4], a[5], a[6], a[0]], [float(v) for v in m.group(3).split(",")], int(m.group(4))


def setting(number):
    """One of the arm's ``$$`` settings, e.g. ``$29=130.000 (LINKAGE1 Link length)`` → 130.0."""
    for line in HARDWARE["settings"]:
        m = re.match(r"\$(\d+) ?=([-\d.]+)", line)
        if m and int(m.group(1)) == number:
            return float(m.group(2))
    raise KeyError(number)


def assert_like_the_arm(joints, pose, move):
    _, want_joints, want_pose, _ = parse(move["status"])
    assert joints == pytest.approx(want_joints, abs=ANGLE_TOL), move["command"]
    assert list(pose) == pytest.approx(want_pose, abs=POSE_TOL), move["command"]


def state_joints(state):
    return [state.angle_X, state.angle_Y, state.angle_Z, state.angle_A]


def state_pose(state):
    return [state.coordinate_X, state.coordinate_Y, state.coordinate_Z,
            state.coordinate_RX, state.coordinate_RY, state.coordinate_RZ]


class TestMT4KinematicsUnit:
    """Pure math and bookkeeping checks."""

    def test_geometry_steps_and_limits_are_the_arms_settings(self):
        assert (mt4.LINK1, mt4.LINK2, mt4.CENTER_OFFSET, mt4.HEAD_OFFSET, mt4.CENTER_HEIGHT, mt4.HEAD_HEIGHT) == \
            tuple(setting(n) for n in (29, 30, 31, 32, 33, 34))
        # the firmware's axes: $1x0 a = J4, $1x4 e = J1, $1x5 f = J2, $1x6 g = J3
        assert mt4.STEPS_PER_DEG == tuple(setting(n) for n in (104, 105, 106, 100))
        assert mt4.JOINT_LIMITS_DEG == tuple((-setting(140 + n), setting(130 + n)) for n in (4, 5, 6, 0))
        assert (mt4.MAX_J2_MINUS_J3, mt4.MAX_J3_MINUS_J2) == (setting(53), setting(54))

    def test_fk_zero_is_the_home_pose(self):
        assert MT4Kinematics().forward([0.0] * 4) == pytest.approx(HOME, abs=1e-9)
        assert parse(HARDWARE["start"])[2] == list(HOME)

    def test_the_flange_direction_is_j1_plus_j4(self):
        assert MT4Kinematics().forward([40.0, 30.0, 25.0, 30.0])[3:] == (0.0, 0.0, 70.0)

    @pytest.mark.parametrize("joints", [
        (0.0, 0.0, 0.0), (30.0, 20.0, 10.0), (-100.0, -30.0, 25.0), (140.0, 70.0, 100.0), (5.0, 45.0, -15.0),
    ])
    def test_ik_roundtrip(self, joints):
        kin = MT4Kinematics()
        x, y, z = kin.forward(list(joints) + [0.0])[:3]
        assert kin.inverse(x, y, z) == pytest.approx(joints, abs=1e-9)

    def test_ik_has_no_solution_beyond_the_links_reach(self):
        kin = MT4Kinematics()
        assert kin.inverse(400.0, 0.0, 100.0) is None      # further than both links stretched out
        assert kin.inverse(80.0, 0.0, 125.57) is None      # on the J2 axis itself
        assert kin.inverse(200.0, 0.0, 150.0) is not None

    def test_limit_errors(self):
        kin = MT4Kinematics()
        assert kin.limit_error([145.0, 80.0, 110.0, 180.0]) is None
        assert kin.limit_error([-124.0, -36.0, -16.0, -180.0]) is None
        assert kin.limit_error([145.01, 0, 0, 0]) == "Error,A102,Soft limit:X"
        assert kin.limit_error([0, -36.01, 0, 0]) == "Error,A102,Soft limit:Y"
        assert kin.limit_error([0, 0, 110.01, 0]) == "Error,A102,Soft limit:Z"
        # the firmware looks at A first, then X, Y, Z, then at J2 against J3
        assert kin.limit_error([150.0, 85.0, 0, 200.0]) == "Error,A102,Soft limit:A"
        assert kin.limit_error([150.0, 85.0, 0, 0]) == "Error,A102,Soft limit:X"
        assert kin.limit_error([0, 45.0, -15.0, 0]) is None
        assert kin.limit_error([0, 46.0, -15.0, 0]) == mt4.ANGLES_TOO_BIG
        assert kin.limit_error([0, -36.0, 24.5, 0]) == mt4.ANGLES_TOO_SMALL
        assert not kin.within_limits([0, 46.0, -15.0, 0])

    def test_joints_stop_on_whole_motor_steps(self):
        motion = MT4Motion()
        assert motion.joint_move({"X": 30, "Y": 0, "Z": 0, "A": 45}) == (["ok"], True)
        assert motion.steps == [1067, 0, 0, 1980]
        assert motion.joints == pytest.approx([30.009, 0.0, 0.0, 44.999], abs=ANGLE_TOL)
        assert motion.pose == pytest.approx((199.168, 115.031, 255.57, 0.0, 0.0, 75.008), abs=POSE_TOL)
        # already there: "ok", and no motor turns
        assert motion.joint_move({"X": 30}) == (["ok"], False)

    def test_incremental_steps_add_to_the_target_not_the_reported_angle(self):
        motion = MT4Motion()
        moved = [motion.joint_move({"X": 0.01}, incremental=True).moved for _ in range(3)]
        assert moved == [False, True, False]    # 0.36, 0.71, 1.07 steps
        assert motion.steps[0] == 1
        motion.cartesian_move({"X": 200, "Y": 0, "Z": 150, "A": 0})
        assert motion.pose[:3] == pytest.approx((200.012, 0.0, 150.024), abs=POSE_TOL)
        motion.cartesian_move({"Z": 5}, incremental=True)
        assert motion.cart_target == [200.0, 0.0, 155.0, 0.0]

    def test_a_is_the_flange_direction_except_on_linear_moves(self):
        motion = MT4Motion()
        motion.joint_move({"X": 7, "Y": -3.5, "Z": 4, "A": 19.3})           # the flange at Rz 26.3
        assert motion.pose[5] == pytest.approx(26.3, abs=0.03)
        assert motion.cartesian_move({"X": 200, "Y": 40, "Z": 160, "A": 25}).lines == [mt4.CARTESIAN_MODE_INFO, "ok"]
        assert motion.pose[5] == pytest.approx(25.0, abs=0.03)             # G00: A
        assert motion.joints[3] == pytest.approx(25.0 - motion.joints[0], abs=0.03)
        motion.cartesian_move({"X": 210, "A": 40}, linear=True)            # G01: back to 26.3, whatever A is
        assert motion.pose[5] == pytest.approx(26.3, abs=0.03)
        motion.cartesian_move({"Z": 5}, incremental=True)                  # G00 again: the linear move's A
        assert motion.pose[5] == pytest.approx(40.0, abs=0.03)
        motion.cartesian_move({"A": -60}, linear=True)                     # a linear move's A is only remembered
        assert motion.pose[5] == pytest.approx(26.3, abs=0.03)
        motion.cartesian_move({}, incremental=True)
        assert motion.pose[5] == pytest.approx(-60.0, abs=0.03)

    def test_the_first_coordinate_move_after_joint_moves_starts_at_rz_zero(self):
        motion = MT4Motion()
        motion.joint_move({"X": 20, "Y": 10, "Z": 30, "A": 30})
        assert motion.pose[5] == pytest.approx(50.0, abs=0.03)
        before = motion.pose
        motion.cartesian_move({"X": 10}, incremental=True)
        assert motion.pose[5] == pytest.approx(0.0, abs=0.03)
        assert motion.pose[:3] == pytest.approx((before[0] + 10, before[1], before[2]), abs=0.1)
        assert motion.mode == 1

    def test_the_first_joint_move_after_coordinate_moves_starts_from_the_reported_angles(self):
        motion = MT4Motion()
        motion.cartesian_move({"X": 200, "Y": 0, "Z": 150, "A": 0})
        reported = motion.joints
        assert motion.joint_move({"Z": 2.09}, incremental=True).lines == [mt4.ANGLE_MODE_INFO, "ok"]
        assert motion.joint_target[2] == reported[2] + 2.09
        assert motion.mode == 0

    def test_refused_moves_do_not_move_and_what_they_leave_behind(self):
        motion = MT4Motion()
        motion.cartesian_move({"X": 200, "Y": 0, "Z": 150, "A": 0})
        at = list(motion.steps)
        # out of reach: the message, "ok", and the target stays
        assert motion.cartesian_move({"X": 400, "Z": 100}) == ([mt4.OUTSIDE_BOUNDARY, "ok"], False)
        assert motion.steps == at
        assert motion.cartesian_move({"X": -150}, incremental=True).moved
        assert motion.pose[:3] == pytest.approx((250.0, 0.0, 100.0), abs=0.05)
        # conflicting J2 / J3: the target stays too
        motion.cartesian_move({"X": 200, "Y": 0, "Z": 150})
        assert motion.cartesian_move({"X": 100, "Z": 100}) == ([mt4.ANGLES_TOO_SMALL, "ok"], False)
        assert motion.steps == at
        motion.cartesian_move({"X": 120}, incremental=True)
        assert motion.pose[:3] == pytest.approx((220.0, 0.0, 100.0), abs=0.05)
        # past a soft limit: the target goes back
        motion.cartesian_move({"X": 200, "Y": 0, "Z": 150})
        assert motion.cartesian_move({"Z": -50}) == (["Error,A102,Soft limit:Y", "ok"], False)
        motion.cartesian_move({"Z": 5}, incremental=True)
        assert motion.pose[:3] == pytest.approx((200.0, 0.0, 155.0), abs=0.05)
        # out of reach right after a refused move: that move's error again
        motion.cartesian_move({"X": -200, "Y": -50, "Z": 150})
        assert motion.cartesian_move({"X": 400, "Y": 0, "Z": 100}) == \
            ([mt4.OUTSIDE_BOUNDARY, "Error,A102,Soft limit:X", "ok"], False)
        # a joint move, even a refused one, and the arm takes its bearings again
        # from where it is: the next coordinate move no longer steps from a refused target
        motion.cartesian_move({"X": 100, "Y": 0, "Z": 100})                      # refused (A107): the target stays
        at = motion.pose
        assert motion.joint_move({"Y": 85}) == ([mt4.ANGLE_MODE_INFO, "Error,A102,Soft limit:Y", "ok"], False)
        assert motion.mode == 0                                                  # the mode changes all the same
        motion.cartesian_move({"X": 10}, incremental=True)
        assert motion.pose[:3] == pytest.approx((at[0] + 10, at[1], at[2]), abs=0.1)

    def test_moves_on_the_simulator_state(self):
        state = RobotState()
        mt4.home(state)
        assert state_pose(state) == pytest.approx(HOME, abs=1e-9)
        assert mt4.cartesian_move(state, {"X": 200, "Y": 0, "Z": 150, "A": 0}) == \
            ([mt4.CARTESIAN_MODE_INFO, "ok"], True)
        assert state.motion_mode == 1
        assert state_joints(state) == pytest.approx([0.0, 5.653, 44.381, 0.0], abs=ANGLE_TOL)
        assert mt4.joint_move(state, {"X": 10}, incremental=True) == ([mt4.ANGLE_MODE_INFO, "ok"], True)
        assert state.motion_mode == 0
        # Joints someone set by hand are where the next move starts
        state.angle_X, state.angle_Y, state.angle_Z, state.angle_A = 20.0, 10.0, 30.0, 0.0
        mt4.joint_move(state, {"Y": 5}, incremental=True)
        assert state_joints(state) == pytest.approx([20.0, 15.0, 30.0, 0.0], abs=0.02)

    @pytest.mark.parametrize("command,linear,incremental", [
        ("M20G90G00X1Y2Z3A4", False, False), ("M20G91G01X1", True, True), ("M20 G90 G1 X1", True, False),
        ("M20G90G05X1", False, False), ("m20g91g00x1", False, True),
    ])
    def test_move_lines_are_read_like_the_arm_reads_them(self, command, linear, incremental, monkeypatch):
        seen = {}
        monkeypatch.setattr(mt4, "cartesian_move", lambda state, values, inc, linear: seen.update(
            values=values, incremental=inc, linear=linear))
        mt4.move_from_command(RobotState(), command)
        assert (seen["linear"], seen["incremental"]) == (linear, incremental)
        assert seen["values"]["X"] == 1.0


class TestMT4AgainstHardware:
    """The real arm's numbers (tests/data/mt4_hardware_poses.json)."""

    @pytest.mark.parametrize("move", MOVES, ids=[f"{i}:{m['command']}" for i, m in enumerate(MOVES)])
    def test_fk_gives_the_pose_the_arm_reports(self, move):
        # from the joints as printed (three decimals), so a little coarser than from the motor steps
        _, joints, pose, _ = parse(move["status"])
        assert MT4Kinematics().forward(joints) == pytest.approx(pose, abs=0.004), move["command"]

    def test_the_arm_only_stops_on_whole_motor_steps(self):
        for move in MOVES:
            for angle, per_deg in zip(move["joints"], mt4.STEPS_PER_DEG):
                steps = angle * per_deg
                assert abs(steps - round(steps)) < 0.05, (move["command"], angle)

    def test_motion_replays_the_session_like_the_arm(self):
        motion = MT4Motion()
        for move in MOVES:
            command = move["command"]
            values = {axis: float(value) for axis, value in re.findall(r"([XYZA])([-\d.]+)", command[3:])}
            if command.startswith("M21"):
                result = motion.joint_move(values, "G91" in command)
            else:
                result = motion.cartesian_move(values, "G91" in command, linear="G01" in command)
            assert_like_the_arm(motion.joints, motion.pose, move)
            assert result.lines == move["replies"] + ["ok"], command
            assert motion.mode == parse(move["status"])[3], command

    @pytest.mark.parametrize("use_json_config", [False, True], ids=["built-in handlers", "JSON config"])
    def test_simulator_replays_the_session_like_the_arm(self, use_json_config):
        sim = MT4Simulator(use_json_config=use_json_config)
        sent = []
        sim._send_response = sent.append
        sim._handle_command("?")
        assert sent == [HARDWARE["start"]]
        for move in MOVES:
            sent.clear()
            sim._handle_command(move["command"])
            assert sent == move["replies"] + ["ok"], move["command"]
            assert_like_the_arm(state_joints(sim.state), state_pose(sim.state), move)
            assert sim.state.motion_mode == parse(move["status"])[3], move["command"]
        # homing: back to zero joints in angle mode
        sim._handle_command("M20G90G00X200Y0Z150A30")
        sim._handle_command("o105=8")
        assert sim.state.state == "Home"
        assert mirobot_status_line(sim.state).replace("<Home", "<Idle") == HARDWARE["start"]

    def test_reports_only_when_the_motors_turned(self):
        """Over the port: the arm reports once after a move, and not at all when it did not move."""
        sim = MT4Simulator()
        port = sim.start()
        serial = MockSerial(port, timeout=0.05, virtual_port=sim._virtual_port)
        sim.set_auto_report(True)

        def lines_after(command, seconds=0.5):
            serial.write((command + "\r\n").encode())
            out, end = [], time.time() + seconds
            while time.time() < end:
                line = serial.readline().decode().strip()
                if line:
                    out.append(line)
            return out

        try:
            moved = lines_after("M21G90G00X30Y0Z0A0")
            assert moved[0] == "ok" and len(moved) == 2
            assert parse(moved[1])[:2] == ("Idle", [30.009, 0.0, 0.0, 0.0])
            assert lines_after("M21G90G00X30Y0Z0A0") == ["ok"]                       # already there
            assert lines_after("M21G90G00X150") == ["Error,A102,Soft limit:X", "ok"]   # refused
            assert parse(lines_after("?")[0])[1] == [30.009, 0.0, 0.0, 0.0]
        finally:
            serial.close()
            sim.stop()

    def test_the_driver_reads_what_the_arm_reports(self, mt4_with_sim):
        robot, sim = mt4_with_sim
        robot.writeCoordinate(0, 0, 180, -80, 200, 30)
        time.sleep(0.3)
        move = next(m for m in MOVES if m["command"] == "M20G90G00X180Y-80Z200A30")
        assert [float(robot.getAngle(n)) for n in (1, 2, 3, 4)] == pytest.approx(move["joints"], abs=ANGLE_TOL)
        assert [float(robot.getCoordinate(n)) for n in (1, 2, 3)] == pytest.approx(move["pose"][:3], abs=POSE_TOL)
        # the fourth coordinate is the flange's direction, the arm's Rz
        assert float(robot.getCoordinate(4)) == pytest.approx(move["pose"][5], abs=POSE_TOL)
