"""Mirobot forward / inverse kinematics from the official URDF chain.

Source geometry: ``wlkata_mirobot_description.urdf`` (6 revolute joints).
TCP offset matches the RobotViewer Mirobot config: ``[0, 0, 0.02428]`` m
in link6 frame.

Joint order (degrees in simulator state):
    J1..J6  <->  angle_X, angle_Y, angle_Z, angle_A, angle_B, angle_C

Cartesian state (mm / degrees):
    X, Y, Z, Rx, Ry, Rz  <->  coordinate_* fields

FK: URDF fixed origins + joint rotations chained in SE(3).
IK: damped least-squares on the geometric Jacobian (same structure as
``kinematics.js``), using pure Python (no numpy).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# URDF joint table (meters, radians for fixed rpy / limits)
# Each entry: origin_xyz, origin_rpy (ROS fixed RPY: Rz*Ry*Rx), axis, limits
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _JointSpec:
    origin_xyz: Tuple[float, float, float]
    origin_rpy: Tuple[float, float, float]
    axis: Tuple[float, float, float]
    lower: float  # rad
    upper: float  # rad


# From wlkata_mirobot_description.urdf
_MIROBOT_JOINTS: Tuple[_JointSpec, ...] = (
    _JointSpec((0.0, 0.0, 0.127), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), -1.919, 2.792),
    _JointSpec((0.029687, 0.0, 0.0), (-1.5708, 0.0, -1.5708), (0.0, 0.0, 1.0), -0.61, 1.221),
    _JointSpec((0.108, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), -2.094, 1.047),
    _JointSpec((0.02, 0.16875, 0.0), (-1.5708, 0.0, 0.0), (0.0, 0.0, 1.0), -3.141, 2.53),
    _JointSpec((0.0, 0.0, 0.0), (1.5708, 0.0, 1.5708), (0.0, 0.0, 1.0), -3.49, 0.523),
    _JointSpec((0.0, 0.0, 0.0), (-1.5708, 0.0, 0.0), (0.0, 0.0, -1.0), -6.283, 6.283),
)

# Tool offset in link6 frame (meters) — RobotViewer mirobot tcpOffset
_TCP_OFFSET_M = (0.0, 0.0, 0.02428)

# DLS parameters (mirrors kinematics.js defaults, slightly relaxed for mm scale)
_IK_LAMBDA = 0.012
_IK_WP = 1.0
_IK_WO = 0.55
_IK_MAX_DQ = 0.22  # rad per iteration
_IK_MAX_ITER = 48
_IK_TOL = 1e-3  # mixed units (m / rad)


# ---------------------------------------------------------------------------
# Minimal SE(3) helpers (row-major 4x4 as list of 4 lists)
# ---------------------------------------------------------------------------

def _mat_mul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    out = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            out[i][j] = (
                a[i][0] * b[0][j]
                + a[i][1] * b[1][j]
                + a[i][2] * b[2][j]
                + a[i][3] * b[3][j]
            )
    return out


def _eye4() -> List[List[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _rot_x(a: float) -> List[List[float]]:
    c, s = math.cos(a), math.sin(a)
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, c, -s, 0.0],
        [0.0, s, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _rot_y(a: float) -> List[List[float]]:
    c, s = math.cos(a), math.sin(a)
    return [
        [c, 0.0, s, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s, 0.0, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _rot_z(a: float) -> List[List[float]]:
    c, s = math.cos(a), math.sin(a)
    return [
        [c, -s, 0.0, 0.0],
        [s, c, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _trans(x: float, y: float, z: float) -> List[List[float]]:
    return [
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _rpy_matrix(roll: float, pitch: float, yaw: float) -> List[List[float]]:
    """ROS URDF fixed-axis RPY: R = Rz(yaw) * Ry(pitch) * Rx(roll)."""
    return _mat_mul(_rot_z(yaw), _mat_mul(_rot_y(pitch), _rot_x(roll)))


def _axis_angle(axis: Sequence[float], angle: float) -> List[List[float]]:
    x, y, z = axis
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-12:
        return _eye4()
    x, y, z = x / n, y / n, z / n
    c, s = math.cos(angle), math.sin(angle)
    C = 1.0 - c
    return [
        [c + x * x * C, x * y * C - z * s, x * z * C + y * s, 0.0],
        [y * x * C + z * s, c + y * y * C, y * z * C - x * s, 0.0],
        [z * x * C - y * s, z * y * C + x * s, c + z * z * C, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_vec3(R: List[List[float]], v: Sequence[float]) -> Tuple[float, float, float]:
    return (
        R[0][0] * v[0] + R[0][1] * v[1] + R[0][2] * v[2],
        R[1][0] * v[0] + R[1][1] * v[1] + R[1][2] * v[2],
        R[2][0] * v[0] + R[2][1] * v[1] + R[2][2] * v[2],
    )


def _cross(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _rotation_to_rpy_zyx(R: List[List[float]]) -> Tuple[float, float, float]:
    """Extract ZYX Euler (yaw, pitch, roll) then return (Rx, Ry, Rz) in degrees.

    Rx = roll about X, Ry = pitch about Y, Rz = yaw about Z — matches common
    robot status RxRyRz ordering after converting rad→deg.
    """
    # ZYX intrinsic: R = Rz(yaw) * Ry(pitch) * Rx(roll)
    sy = -R[2][0]
    sy = max(-1.0, min(1.0, sy))
    pitch = math.asin(sy)
    if abs(sy) < 0.999999:
        roll = math.atan2(R[2][1], R[2][2])
        yaw = math.atan2(R[1][0], R[0][0])
    else:
        roll = math.atan2(-R[0][1], R[1][1])
        yaw = 0.0
    return (
        math.degrees(roll),
        math.degrees(pitch),
        math.degrees(yaw),
    )


def _rpy_deg_to_matrix(rx_deg: float, ry_deg: float, rz_deg: float) -> List[List[float]]:
    return _rpy_matrix(
        math.radians(rx_deg),
        math.radians(ry_deg),
        math.radians(rz_deg),
    )


def _rot_log_vec(R_err: List[List[float]]) -> Tuple[float, float, float]:
    """Rotation matrix log → axis-angle vector (rad)."""
    tr = R_err[0][0] + R_err[1][1] + R_err[2][2]
    cos_th = max(-1.0, min(1.0, (tr - 1.0) * 0.5))
    theta = math.acos(cos_th)
    if theta < 1e-10:
        return (0.0, 0.0, 0.0)
    if abs(theta - math.pi) < 1e-6:
        # near 180° — pick largest diagonal
        return (theta, 0.0, 0.0)
    s = 0.5 / math.sin(theta)
    return (
        s * (R_err[2][1] - R_err[1][2]) * theta,
        s * (R_err[0][2] - R_err[2][0]) * theta,
        s * (R_err[1][0] - R_err[0][1]) * theta,
    )


def _mat3_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    out = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            out[i][j] = A[i][0] * B[0][j] + A[i][1] * B[1][j] + A[i][2] * B[2][j]
    return out


def _mat3_T(A: List[List[float]]) -> List[List[float]]:
    return [[A[j][i] for j in range(3)] for i in range(3)]


def _solve_linear6(A: List[float], b: List[float]) -> Optional[List[float]]:
    """Solve 6x6 system A x = b (A row-major flat). Partial pivoting GE."""
    n = 6
    M = list(A)
    y = list(b)
    x = [0.0] * n
    for k in range(n - 1):
        max_row = k
        max_val = abs(M[k * n + k])
        for i in range(k + 1, n):
            v = abs(M[i * n + k])
            if v > max_val:
                max_val = v
                max_row = i
        if max_val < 1e-14:
            return None
        if max_row != k:
            for c in range(n):
                M[k * n + c], M[max_row * n + c] = M[max_row * n + c], M[k * n + c]
            y[k], y[max_row] = y[max_row], y[k]
        piv = M[k * n + k]
        for i in range(k + 1, n):
            f = M[i * n + k] / piv
            for c in range(k, n):
                M[i * n + c] -= f * M[k * n + c]
            y[i] -= f * y[k]
    for i in range(n - 1, -1, -1):
        s = y[i]
        for c in range(i + 1, n):
            s -= M[i * n + c] * x[c]
        piv = M[i * n + i]
        if abs(piv) < 1e-14:
            return None
        x[i] = s / piv
    return x


class MirobotKinematics:
    """FK / IK for the WLKATA Mirobot using the shipped URDF geometry."""

    def __init__(
        self,
        tcp_offset_m: Tuple[float, float, float] = _TCP_OFFSET_M,
        joints: Tuple[_JointSpec, ...] = _MIROBOT_JOINTS,
    ):
        self.tcp_offset_m = tcp_offset_m
        self.joints = joints

    def clamp_joints_rad(self, q: Sequence[float]) -> List[float]:
        out = []
        for i, qi in enumerate(q):
            lo, hi = self.joints[i].lower, self.joints[i].upper
            out.append(max(lo, min(hi, float(qi))))
        return out

    def forward_all(
        self, joint_deg: Sequence[float]
    ) -> Tuple[List[List[float]], List[Tuple[float, float, float]], List[Tuple[float, float, float]]]:
        """Return (T_tcp, joint_origins_world, joint_axes_world).

        joint_origins_world / joint_axes_world are length 6, used for Jacobian.
        """
        T = _eye4()
        origins: List[Tuple[float, float, float]] = []
        axes_w: List[Tuple[float, float, float]] = []
        q_rad = [math.radians(a) for a in joint_deg]

        for i, spec in enumerate(self.joints):
            ox, oy, oz = spec.origin_xyz
            rr, rp, ry = spec.origin_rpy
            T_fixed = _mat_mul(_trans(ox, oy, oz), _rpy_matrix(rr, rp, ry))
            T = _mat_mul(T, T_fixed)
            # joint origin in world before joint rotation
            origins.append((T[0][3], T[1][3], T[2][3]))
            # axis in world: R_current * axis_local
            R = [[T[r][c] for c in range(3)] for r in range(3)]
            aw = _mat_vec3(R, spec.axis)
            n = math.sqrt(aw[0] ** 2 + aw[1] ** 2 + aw[2] ** 2) or 1.0
            axes_w.append((aw[0] / n, aw[1] / n, aw[2] / n))
            T = _mat_mul(T, _axis_angle(spec.axis, q_rad[i]))

        # TCP
        tx, ty, tz = self.tcp_offset_m
        T = _mat_mul(T, _trans(tx, ty, tz))
        return T, origins, axes_w

    def forward(self, joint_deg: Sequence[float]) -> Tuple[float, float, float, float, float, float]:
        """FK: joint degrees → (X,Y,Z mm, Rx,Ry,Rz deg)."""
        T, _, _ = self.forward_all(joint_deg)
        x_mm = T[0][3] * 1000.0
        y_mm = T[1][3] * 1000.0
        z_mm = T[2][3] * 1000.0
        R = [[T[r][c] for c in range(3)] for r in range(3)]
        rx, ry, rz = _rotation_to_rpy_zyx(R)
        return (x_mm, y_mm, z_mm, rx, ry, rz)

    def _pose_error(
        self,
        joint_deg: Sequence[float],
        target_mm_rpy: Sequence[float],
    ) -> List[float]:
        T, _, _ = self.forward_all(joint_deg)
        px, py, pz = T[0][3], T[1][3], T[2][3]
        tx, ty, tz = (
            target_mm_rpy[0] / 1000.0,
            target_mm_rpy[1] / 1000.0,
            target_mm_rpy[2] / 1000.0,
        )
        e = [tx - px, ty - py, tz - pz, 0.0, 0.0, 0.0]
        R_ee = [[T[r][c] for c in range(3)] for r in range(3)]
        R_tgt4 = _rpy_deg_to_matrix(target_mm_rpy[3], target_mm_rpy[4], target_mm_rpy[5])
        R_tgt3 = [[R_tgt4[r][c] for c in range(3)] for r in range(3)]
        # R_err = R_tgt * R_ee^T
        R_err = _mat3_mul(R_tgt3, _mat3_T(R_ee))
        rv = _rot_log_vec(R_err)
        e[3], e[4], e[5] = rv
        return e

    def _jacobian(self, joint_deg: Sequence[float]) -> List[float]:
        """6x6 geometric Jacobian, row-major flat (m, rad)."""
        T, origins, axes = self.forward_all(joint_deg)
        pee = (T[0][3], T[1][3], T[2][3])
        J = [0.0] * 36
        for j in range(6):
            z = axes[j]
            r = (pee[0] - origins[j][0], pee[1] - origins[j][1], pee[2] - origins[j][2])
            v = _cross(z, r)
            J[0 * 6 + j] = v[0]
            J[1 * 6 + j] = v[1]
            J[2 * 6 + j] = v[2]
            J[3 * 6 + j] = z[0]
            J[4 * 6 + j] = z[1]
            J[5 * 6 + j] = z[2]
        return J

    def inverse(
        self,
        target_mm_rpy: Sequence[float],
        seed_deg: Optional[Sequence[float]] = None,
        max_iter: int = _IK_MAX_ITER,
        tol: float = _IK_TOL,
    ) -> Tuple[List[float], bool]:
        """IK: Cartesian (mm, deg RPY) → joint degrees.

        Returns (joints_deg, converged).
        """
        if seed_deg is None:
            q = [0.0] * 6
        else:
            q = [float(a) for a in seed_deg]

        swp = math.sqrt(_IK_WP)
        swo = math.sqrt(_IK_WO)
        lam2 = _IK_LAMBDA * _IK_LAMBDA

        for _ in range(max_iter):
            e = self._pose_error(q, target_mm_rpy)
            n2 = sum(x * x for x in e)
            if math.sqrt(n2) < tol:
                return q, True

            J = self._jacobian(q)
            # weight J and e
            Jw = list(J)
            for r in range(3):
                for c in range(6):
                    Jw[r * 6 + c] *= swp
            for r in range(3, 6):
                for c in range(6):
                    Jw[r * 6 + c] *= swo
            ew = [e[i] * swp if i < 3 else e[i] * swo for i in range(6)]

            # JJt = Jw * Jw^T + λ²I  (6x6)
            JJt = [0.0] * 36
            for i in range(6):
                for j in range(6):
                    s = 0.0
                    for k in range(6):
                        s += Jw[i * 6 + k] * Jw[j * 6 + k]
                    JJt[i * 6 + j] = s
                JJt[i * 6 + i] += lam2

            x = _solve_linear6(JJt, ew)
            if x is None:
                break

            dq = [0.0] * 6
            for j in range(6):
                s = 0.0
                for i in range(6):
                    s += Jw[i * 6 + j] * x[i]
                dq[j] = s

            dn = math.sqrt(sum(d * d for d in dq))
            if dn > _IK_MAX_DQ:
                sc = _IK_MAX_DQ / dn
                dq = [d * sc for d in dq]

            q_rad = [math.radians(a) + dq[i] for i, a in enumerate(q)]
            q_rad = self.clamp_joints_rad(q_rad)
            q = [math.degrees(a) for a in q_rad]

        e = self._pose_error(q, target_mm_rpy)
        ok = math.sqrt(sum(x * x for x in e)) < tol * 5
        return q, ok


# Shared singleton for sim handlers
_DEFAULT_KIN = MirobotKinematics()


def joints_from_state(state) -> List[float]:
    """Map simulator state joint fields → [J1..J6] degrees."""
    return [
        float(state.angle_X),
        float(state.angle_Y),
        float(state.angle_Z),
        float(state.angle_A),
        float(state.angle_B),
        float(state.angle_C),
    ]


def joints_to_state(state, joints_deg: Sequence[float]) -> None:
    state.angle_X = float(joints_deg[0])
    state.angle_Y = float(joints_deg[1])
    state.angle_Z = float(joints_deg[2])
    state.angle_A = float(joints_deg[3])
    state.angle_B = float(joints_deg[4])
    state.angle_C = float(joints_deg[5])


def apply_fk_to_state(state, kin: Optional[MirobotKinematics] = None) -> None:
    """Update Cartesian fields from current joint angles (FK)."""
    kin = kin or _DEFAULT_KIN
    x, y, z, rx, ry, rz = kin.forward(joints_from_state(state))
    state.coordinate_X = x
    state.coordinate_Y = y
    state.coordinate_Z = z
    state.coordinate_RX = rx
    state.coordinate_RY = ry
    state.coordinate_RZ = rz


def apply_ik_to_state(state, kin: Optional[MirobotKinematics] = None) -> bool:
    """Update joint angles from current Cartesian fields (IK).

    Returns True if IK reported convergence.
    """
    kin = kin or _DEFAULT_KIN
    target = (
        float(state.coordinate_X),
        float(state.coordinate_Y),
        float(state.coordinate_Z),
        float(state.coordinate_RX),
        float(state.coordinate_RY),
        float(state.coordinate_RZ),
    )
    seed = joints_from_state(state)
    q, ok = kin.inverse(target, seed_deg=seed)
    joints_to_state(state, q)
    # Leave Cartesian as commanded (G-code target). Joints track via IK.
    return ok
