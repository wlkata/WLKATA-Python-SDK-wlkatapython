"""Mirobot FK/IK simulator tests.

Hardware-calibration cases for writeAngle / writeCoordinate are skipped until
measured values from real hardware are filled in.
"""

import pytest
import time

from wlkatapython.simulator.kinematics import MirobotKinematics, apply_fk_to_state
from wlkatapython.simulator import RobotState


pytestmark = pytest.mark.mirobot


class TestMirobotKinematicsUnit:
    """Pure math checks (no hardware)."""

    def test_fk_zero_returns_six_tuple(self):
        kin = MirobotKinematics()
        pose = kin.forward([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert len(pose) == 6
        assert all(isinstance(v, float) for v in pose)

    def test_fk_changes_with_joint(self):
        kin = MirobotKinematics()
        p0 = kin.forward([0.0] * 6)
        p1 = kin.forward([30.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        # Base yaw should move X/Y (or at least not be identical pose)
        assert p0 != p1

    def test_ik_roundtrip_near_seed(self):
        """IK should approximately recover joints for a reachable seed pose."""
        kin = MirobotKinematics()
        seed = [10.0, 15.0, -10.0, 5.0, 20.0, 0.0]
        target = kin.forward(seed)
        q, ok = kin.inverse(target, seed_deg=seed)
        assert ok
        for a, b in zip(q, seed):
            assert abs(a - b) < 2.0  # degrees — numerical DLS tolerance

    def test_apply_fk_to_state(self):
        state = RobotState()
        state.angle_X = 0.0
        state.angle_Y = 0.0
        state.angle_Z = 0.0
        state.angle_A = 0.0
        state.angle_B = 0.0
        state.angle_C = 0.0
        apply_fk_to_state(state)
        kin = MirobotKinematics()
        x, y, z, rx, ry, rz = kin.forward([0.0] * 6)
        assert abs(state.coordinate_X - x) < 1e-6
        assert abs(state.coordinate_Y - y) < 1e-6
        assert abs(state.coordinate_Z - z) < 1e-6


class TestMirobotKinematicsHardwareCalibration:
    """Fill EXPECTED_* from real hardware, then un-skip.

    Mapping (SDK / G-code):
      writeAngle axes X,Y,Z,A,B,C  ->  joints J1..J6 (degrees)
      writeCoordinate X,Y,Z,A,B,C  ->  mm and Rx,Ry,Rz (degrees)

    After angle move, sim runs FK → coordinate_*.
    After cartesian move, sim runs IK → angle_*.
    """

    # --- placeholders: replace with measured hardware values ---
    # Absolute writeAngle(0, j1..j6) then getStatus / sim coordinates
    ANGLE_ABS_CMD = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)  # X Y Z A B C deg
    ANGLE_ABS_EXPECTED_CART = None  # (X, Y, Z, Rx, Ry, Rz) mm/deg or None

    # Incremental writeAngle(1, ...) from a known base pose
    ANGLE_INC_BASE = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    ANGLE_INC_DELTA = (5.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    ANGLE_INC_EXPECTED_CART = None

    # Absolute writeCoordinate
    CART_ABS_CMD = (200.0, 0.0, 150.0, 0.0, 0.0, 0.0)  # X Y Z A B C
    CART_ABS_EXPECTED_JOINTS = None  # (X,Y,Z,A,B,C) joint deg or None

    # Incremental writeCoordinate from base
    CART_INC_BASE = (200.0, 0.0, 150.0, 0.0, 0.0, 0.0)
    CART_INC_DELTA = (10.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    CART_INC_EXPECTED_JOINTS = None

    @pytest.mark.skip(reason="Fill ANGLE_ABS_EXPECTED_CART from real hardware, then enable")
    def test_write_angle_absolute_matches_hardware_cartesian(self, mirobot_with_sim):
        robot, sim = mirobot_with_sim
        x, y, z, a, b, c = self.ANGLE_ABS_CMD
        robot.writeAngle(0, x=x, y=y, z=z, a=a, b=b, c=c)
        time.sleep(0.4)
        exp = self.ANGLE_ABS_EXPECTED_CART
        assert exp is not None
        assert sim.state.coordinate_X == pytest.approx(exp[0], abs=1.0)
        assert sim.state.coordinate_Y == pytest.approx(exp[1], abs=1.0)
        assert sim.state.coordinate_Z == pytest.approx(exp[2], abs=1.0)
        assert sim.state.coordinate_RX == pytest.approx(exp[3], abs=2.0)
        assert sim.state.coordinate_RY == pytest.approx(exp[4], abs=2.0)
        assert sim.state.coordinate_RZ == pytest.approx(exp[5], abs=2.0)

    @pytest.mark.skip(reason="Fill ANGLE_INC_EXPECTED_CART from real hardware, then enable")
    def test_write_angle_incremental_matches_hardware_cartesian(self, mirobot_with_sim):
        robot, sim = mirobot_with_sim
        bx, by, bz, ba, bb, bc = self.ANGLE_INC_BASE
        robot.writeAngle(0, x=bx, y=by, z=bz, a=ba, b=bb, c=bc)
        time.sleep(0.3)
        dx, dy, dz, da, db, dc = self.ANGLE_INC_DELTA
        robot.writeAngle(1, x=dx, y=dy, z=dz, a=da, b=db, c=dc)
        time.sleep(0.4)
        exp = self.ANGLE_INC_EXPECTED_CART
        assert exp is not None
        assert sim.state.coordinate_X == pytest.approx(exp[0], abs=1.0)
        assert sim.state.coordinate_Y == pytest.approx(exp[1], abs=1.0)
        assert sim.state.coordinate_Z == pytest.approx(exp[2], abs=1.0)

    @pytest.mark.skip(reason="Fill CART_ABS_EXPECTED_JOINTS from real hardware, then enable")
    def test_write_coordinate_absolute_matches_hardware_joints(self, mirobot_with_sim):
        robot, sim = mirobot_with_sim
        x, y, z, a, b, c = self.CART_ABS_CMD
        robot.writeCoordinate(0, 0, x=x, y=y, z=z, a=a, b=b, c=c)
        time.sleep(0.5)
        exp = self.CART_ABS_EXPECTED_JOINTS
        assert exp is not None
        assert sim.state.angle_X == pytest.approx(exp[0], abs=2.0)
        assert sim.state.angle_Y == pytest.approx(exp[1], abs=2.0)
        assert sim.state.angle_Z == pytest.approx(exp[2], abs=2.0)
        assert sim.state.angle_A == pytest.approx(exp[3], abs=2.0)
        assert sim.state.angle_B == pytest.approx(exp[4], abs=2.0)
        assert sim.state.angle_C == pytest.approx(exp[5], abs=2.0)

    @pytest.mark.skip(reason="Fill CART_INC_EXPECTED_JOINTS from real hardware, then enable")
    def test_write_coordinate_incremental_matches_hardware_joints(self, mirobot_with_sim):
        robot, sim = mirobot_with_sim
        bx, by, bz, ba, bb, bc = self.CART_INC_BASE
        robot.writeCoordinate(0, 0, x=bx, y=by, z=bz, a=ba, b=bb, c=bc)
        time.sleep(0.4)
        dx, dy, dz, da, db, dc = self.CART_INC_DELTA
        robot.writeCoordinate(0, 1, x=dx, y=dy, z=dz, a=da, b=db, c=dc)
        time.sleep(0.5)
        exp = self.CART_INC_EXPECTED_JOINTS
        assert exp is not None
        assert sim.state.angle_X == pytest.approx(exp[0], abs=2.0)
        assert sim.state.angle_Y == pytest.approx(exp[1], abs=2.0)
        assert sim.state.angle_Z == pytest.approx(exp[2], abs=2.0)
