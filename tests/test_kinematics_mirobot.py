"""Mirobot FK / IK and the simulator, checked against a real arm.

``tests/data/mirobot_hardware_poses.json`` records a real Mirobot (firmware
Mirobot,20240820, EXbox,20230710) driven through 47 joint (M21) and coordinate
(M20) moves from home: each command, what the arm replied besides "ok", and
the status it reported once Idle. The simulator replays the same commands and
has to reach the same joints and report the same poses.
"""

import json
import pathlib

import pytest

from wlkatapython.simulator import MirobotSimulator, RobotState
from wlkatapython.simulator.kinematics import (
    MirobotKinematics,
    apply_cartesian_move,
    apply_fk_to_state,
    euler_to_matrix,
    matrix_to_euler,
)
from wlkatapython.simulator.simulated_hardware import mirobot_status_line


pytestmark = pytest.mark.mirobot

HARDWARE = json.loads((pathlib.Path(__file__).parent / "data" / "mirobot_hardware_poses.json").read_text())
MOVES = HARDWARE["moves"]
HOME = (198.67, 0.0, 230.72, 0.0, 0.0, 0.0)


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def assert_pose(actual, expected, mm, deg, what=""):
    for i in range(3):
        assert actual[i] == pytest.approx(expected[i], abs=mm), f"{what} position {i}: {actual} vs {expected}"
    for i in range(3, 6):
        assert abs(wrap(actual[i] - expected[i])) <= deg, f"{what} orientation {i}: {actual} vs {expected}"


def state_pose(state):
    return (state.coordinate_X, state.coordinate_Y, state.coordinate_Z,
            state.coordinate_RX, state.coordinate_RY, state.coordinate_RZ)


def state_joints(state):
    return (state.angle_X, state.angle_Y, state.angle_Z, state.angle_A, state.angle_B, state.angle_C)


class TestMirobotKinematicsUnit:
    """Pure math checks."""

    def test_fk_zero_is_the_home_pose(self):
        assert_pose(MirobotKinematics().forward([0.0] * 6), HOME, 1e-9, 1e-9)

    def test_ik_roundtrip_near_seed(self):
        kin = MirobotKinematics()
        seed = [10.0, 15.0, -10.0, 5.0, 20.0, 0.0]
        q, ok = kin.inverse(kin.forward(seed), seed_deg=seed)
        assert ok
        assert q == pytest.approx(seed, abs=1e-6)

    def test_ik_picks_the_solution_nearest_the_current_joints(self):
        kin = MirobotKinematics()
        # The same pose with the wrist turned the other way: J4 + 180, -J5 - 180, J6 + 180
        pose = kin.forward([0.0, 0.0, 0.0, 30.0, -30.0, 0.0])
        q, _ = kin.inverse(pose, seed_deg=[0.0] * 6)
        assert q == pytest.approx([0.0, 0.0, 0.0, 30.0, -30.0, 0.0], abs=1e-6)
        q, _ = kin.inverse(pose, seed_deg=[0.0, 0.0, 0.0, -150.0, -150.0, 180.0])
        assert q == pytest.approx([0.0, 0.0, 0.0, -150.0, -150.0, 180.0], abs=1e-6)

    def test_ik_rejects_poses_outside_the_workspace(self):
        seed = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        q, ok = MirobotKinematics().inverse((400.0, 0.0, 200.0, 0.0, 0.0, 0.0), seed_deg=seed)
        assert not ok and q == seed
        # Within reach but past a joint limit (J2 >= -35°)
        _, ok = MirobotKinematics().inverse((100.0, 0.0, 230.72, 0.0, 0.0, 0.0))
        assert not ok

    def test_euler_triple_nearest_j4(self):
        R = euler_to_matrix(0.0, -100.0, 0.0)
        assert matrix_to_euler(R, near_rx_deg=0.0) == pytest.approx((0.0, -100.0, 0.0), abs=1e-9)
        other = matrix_to_euler(R, near_rx_deg=170.0)
        assert all(abs(wrap(x - y)) < 1e-9 for x, y in zip(other, (180.0, -80.0, 180.0))), other
        # Gimbal lock: Rx = the hint, Rz carries the rest
        assert matrix_to_euler(euler_to_matrix(20.0, -90.0, 10.0), near_rx_deg=0.0) == pytest.approx((0.0, -90.0, 30.0), abs=1e-6)

    def test_apply_fk_to_state(self):
        state = RobotState()
        apply_fk_to_state(state)
        assert_pose(state_pose(state), HOME, 1e-9, 1e-9)
        assert state.cartesian_target == pytest.approx(list(HOME), abs=1e-9)

    def test_g91_steps_add_to_the_target_not_the_reported_pose(self):
        state = RobotState()
        apply_fk_to_state(state)
        assert apply_cartesian_move(state, {"X": 200, "Y": 50, "Z": 200, "A": 0, "B": 0, "C": 0})
        assert state.coordinate_Z == pytest.approx(199.72, abs=0.01)   # reported 0.28 mm low
        assert apply_cartesian_move(state, {"Z": 8}, incremental=True)
        assert state.coordinate_Z == pytest.approx(207.72, abs=0.01)   # 200 + 8, still 0.28 mm low
        # Editing the reported pose by hand makes it the new starting point
        state.coordinate_Z = 190.0
        assert apply_cartesian_move(state, {"Z": 10}, incremental=True)
        assert state.coordinate_Z == pytest.approx(199.72, abs=0.01)


class TestMirobotAgainstHardware:
    """The real arm's numbers (tests/data/mirobot_hardware_poses.json)."""

    @pytest.mark.parametrize("move", MOVES, ids=[m["command"] for m in MOVES])
    def test_fk_gives_the_pose_the_arm_reports(self, move):
        # The firmware prints three decimals; after a coordinate move its orientation
        # is up to 0.01° from FK of the joints as printed (finer joint values inside)
        deg = 0.005 if move["command"].startswith("M21") else 0.02
        assert_pose(MirobotKinematics().forward(move["joints"]), move["pose"], 0.005, deg, move["command"])

    def test_simulator_replays_the_session_like_the_arm(self):
        sim = MirobotSimulator()
        sent = []
        sim._send_response = sent.append
        assert_pose(state_pose(sim.state), HOME, 1e-9, 1e-9)
        for move in MOVES:
            sent.clear()
            sim._handle_command(move["command"])
            assert sent[-1] == "ok", move["command"]
            assert sent[:-1] == move["replies"], move["command"]
            # Joint moves land on the commanded angles; the arm's steppers stop within 0.01°
            for got, want in zip(state_joints(sim.state), move["joints"]):
                assert abs(wrap(got - want)) <= 0.05, (move["command"], state_joints(sim.state), move["joints"])
            assert_pose(state_pose(sim.state), move["pose"], 0.05, 0.05, move["command"])

    def test_status_line_has_the_firmware_format(self):
        state = RobotState()
        apply_fk_to_state(state)
        assert mirobot_status_line(state) == HARDWARE["start"]
