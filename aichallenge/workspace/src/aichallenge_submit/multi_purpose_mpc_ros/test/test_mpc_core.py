"""修正版 MPC（core/MPC.py）の振る舞いテスト（方針 §5「決定論的検査」）。

実行はコンテナ内: aichallenge/research_tools/test.sh（ノードと同じ .venv の python で unittest、system python で pytest の両方）。
unittest だけで書く（.venv に pytest が無い）。reference_path.py は map.py 経由で skimage が要るので import しない。
地図や経路ファイルは使わず、偽の経路（waypoint 間隔と v_ref と曲率を waypoint ごとに変える）と偽 OSQP で検査する。

固定する振る舞い:
  (a) ステアリングレート制約の幅が delta_s / max(v_ref, MIN_V_FOR_DT) に比例する（修正 (a): 制御周期 Ts ではなく空間ステップの時間）
  (b) 2回目以降の get_control では setup() を呼ばず update() に q/l/u/Ax（Q を変えたら Px も）を渡す。
      疎行列パターンが変わったら setup() し直す（修正 (b): ウォームスタート）
  (c) 解に NaN・受け入れないステータス・舵角の箱制約違反があれば解を棄却し、前回の予測入力の2ステップ目に切り替え、
      舵角レート制限を掛けて有限の値を出す（修正 (c): 解の検証とフォールバック）
  (d) 新しい疎行列の組み立て（_build_constraint_matrix）が、公式 a284274 の密行列の組み立てと同じ行列になる
  (e) 本物の osqp（.venv では 0.6.7）でも2回の get_control が有限の出力を返し setup は1回
公式サンプル a284274 の MPC.py を置くと (a)(b)(c) が AttributeError ではなく assert で落ちる（手順5 の完了条件）。
"""
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np
from scipy import sparse

from multi_purpose_mpc_ros.core import MPC as mpc_module
from multi_purpose_mpc_ros.core.MPC import MPC
from multi_purpose_mpc_ros.core.spatial_bicycle_models import BicycleModel

LENGTH = 1.087          # config.yaml bicycle_model.length
WIDTH = 2.30
TS = 1.0 / 40.0         # control_rate 40 Hz
N = 20
NX, NU = 3, 2
DELTA_MAX = np.deg2rad(32.0)
KAPPA_MAX = np.tan(DELTA_MAX) / LENGTH
STEER_RATE_MAX = 0.35   # rad/s
V_MAX = 20.0
MIN_V_FOR_DT = 1.0      # MPC.MIN_V_FOR_DT と同じ値（テスト側で独立に持つ）


class Waypoint:
    """reference_path.Waypoint のうち MPC と BicycleModel が使う属性だけ。"""

    def __init__(self, x, y, psi, kappa, v_ref):
        self.x, self.y, self.psi, self.kappa, self.v_ref = x, y, psi, kappa, v_ref
        self.lb = -3.0
        self.ub = 3.0

    def __sub__(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class FakePath:
    """x 軸に沿った偽 reference path。間隔・v_ref・曲率を waypoint ごとに指定できる（幅 ±3 m、周回扱い）。"""

    def __init__(self, spacings, v_refs, kappas=None, circular=True):
        n = len(spacings)
        kappas = kappas if kappas is not None else [0.0] * n
        self.circular = circular
        self.n_waypoints = n
        self.waypoints = []
        x = 0.0
        for i in range(n):
            self.waypoints.append(Waypoint(x, 0.0, 0.0, kappas[i], v_refs[i]))
            x += spacings[i]
        self.spacings = list(spacings)
        self.segment_lengths = [0.0] + list(spacings[:-1])
        self.path_constraints = None
        self.border_cells = SimpleNamespace(current_wp_id=None)

    def get_waypoint(self, wp_id):
        return self.waypoints[wp_id % self.n_waypoints]

    def update_simple_path_constraints(self, N, safety_margin):
        rows = self.n_waypoints - 1
        self.path_constraints = [np.full((rows, N), 3.0 - safety_margin),
                                 np.full((rows, N), -3.0 + safety_margin)]


def uniform_path(v_ref, n=60, spacing=1.0, kappa=0.0):
    return FakePath([spacing] * n, [v_ref] * n, [kappa] * n)


class SteppingModel(BicycleModel):
    """get_current_waypoint のたびに waypoint を1つ進める車両モデル（経路探索は省く）。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._calls = 0

    def get_current_waypoint(self):
        self.wp_id = self._calls % self.reference_path.n_waypoints
        self._calls += 1
        self.current_waypoint = self.reference_path.waypoints[self.wp_id]


class FakeOSQP:
    """osqp.OSQP の代役。setup/update の回数と引数を記録し、決めた解を返す。"""
    setup_calls = 0
    update_calls = 0
    solve_calls = 0
    setups = []            # setup に渡された dict(P, q, A, l, u)
    updates = []           # update に渡された kwargs
    nan_from_solve = None  # この回数目以降の solve は NaN を返す
    status = "solved"
    kappa_scale = 1.0      # 解の曲率に掛ける倍率（箱制約違反の模擬用）

    @classmethod
    def reset(cls, nan_from_solve=None, status="solved", kappa_scale=1.0):
        cls.setup_calls = 0
        cls.update_calls = 0
        cls.solve_calls = 0
        cls.setups = []
        cls.updates = []
        cls.nan_from_solve = nan_from_solve
        cls.status = status
        cls.kappa_scale = kappa_scale

    @staticmethod
    def solution_controls():
        """ステップごとに違う値: v = 5 + n, kappa = 0.01 * (n + 1)（どのステップを使ったか判別できる）。"""
        n = np.arange(N)
        return np.column_stack([5.0 + n, 0.01 * (n + 1) * FakeOSQP.kappa_scale]).ravel()

    def setup(self, P, q, A, l, u, **kwargs):  # noqa: E741 (osqp のキーワード名に合わせる)
        FakeOSQP.setup_calls += 1
        FakeOSQP.setups.append(dict(P=P, q=np.array(q), A=A, l=np.array(l), u=np.array(u)))

    def update(self, **kwargs):
        FakeOSQP.update_calls += 1
        FakeOSQP.updates.append({k: (np.array(v) if v is not None else None) for k, v in kwargs.items()})

    def solve(self):
        FakeOSQP.solve_calls += 1
        x = np.concatenate([np.zeros(NX * (N + 1)), self.solution_controls()])
        if FakeOSQP.nan_from_solve is not None and FakeOSQP.solve_calls >= FakeOSQP.nan_from_solve:
            x[NX * (N + 1) + 1] = np.nan                 # 1 ステップ目の kappa を NaN に
        return SimpleNamespace(x=x, info=SimpleNamespace(status=FakeOSQP.status, iter=10))


def make_mpc(path):
    car = SteppingModel(path, LENGTH, WIDTH, TS)
    state_constraints = {"xmin": np.array([-np.inf] * 3), "xmax": np.array([np.inf] * 3)}
    input_constraints = {"umin": np.array([0.0, -KAPPA_MAX]), "umax": np.array([V_MAX, KAPPA_MAX])}
    mpc = MPC(car, N, sparse.diags([1.0, 1.0, 1.0]), sparse.diags([1.0, 1.0]), sparse.diags([1.0, 1.0, 1.0]),
              state_constraints, input_constraints, ay_max=6.5, max_steering_rate=STEER_RATE_MAX,
              wp_id_offset=0, use_obstacle_avoidance=False, use_path_constraints_topic=False)
    return mpc, car


def expected_rate_bounds(path, wp_id):
    """(a) の期待値: max_rate * delta_s[n] / max(v_ref[n], MIN_V) / L、n = 0..N-2。"""
    out = []
    for n in range(N - 1):
        wp, nxt = path.get_waypoint(wp_id + n), path.get_waypoint(wp_id + n + 1)
        v = np.clip(wp.v_ref, 0.0, V_MAX)
        out.append(STEER_RATE_MAX * (nxt - wp) / max(v, MIN_V_FOR_DT) / LENGTH)
    return np.array(out)


def n_bounds():
    return NX * (N + 1) + (NX * (N + 1) + NU * N) + (N - 1)   # 等式（x0 と N 段のダイナミクス）+ 箱 + レート


def dense_reference_A(car, path, wp_id):
    """(d) の参照: 公式 a284274 と同じ密行列の組み立て（kron(-I) + A/B ブロック、単位行列、レート差分行列）。"""
    nx_N, nu_N = NX * (N + 1), NU * N
    A = np.zeros((nx_N, nx_N))
    B = np.zeros((nx_N, nu_N))
    for n in range(N):
        wp, nxt = path.get_waypoint(wp_id + n), path.get_waypoint(wp_id + n + 1)
        v_ref = np.clip(wp.v_ref, 0.0, V_MAX)
        _, A_lin, B_lin = car.linearize(v_ref, wp.kappa, nxt - wp)
        A[(n + 1) * NX:(n + 2) * NX, n * NX:(n + 1) * NX] = A_lin
        B[(n + 1) * NX:(n + 2) * NX, n * NU:(n + 1) * NU] = B_lin
    Aeq = np.hstack([np.kron(np.eye(N + 1), -np.eye(NX)) + A, B])
    rate = np.zeros((N - 1, nx_N + nu_N))
    for i in range(N - 1):
        rate[i, nx_N + NU * i + 1] = -1
        rate[i, nx_N + NU * (i + 1) + 1] = 1
    return np.vstack([Aeq, np.eye(nx_N + nu_N), rate])


class MpcCoreBehaviourTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(mpc_module.osqp, "OSQP", FakeOSQP)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(FakeOSQP.reset)
        FakeOSQP.reset()

    # ---- (a) ステアリングレート制約の幅 ----
    def test_a1_rate_bound_ratio_between_two_speeds(self):
        """v_ref 2 → 8 m/s で幅が 1/4 になる（方針 §5 の指定）。"""
        bounds = {}
        for v in (2.0, 8.0):
            FakeOSQP.reset()
            mpc, _ = make_mpc(uniform_path(v))
            mpc.get_control()
            bounds[v] = FakeOSQP.setups[0]["u"][-(N - 1):]
        self.assertEqual(len(FakeOSQP.setups[0]["u"]), n_bounds())
        self.assertTrue(np.allclose(bounds[2.0] / bounds[8.0], 4.0), (bounds[2.0][:3], bounds[8.0][:3]))
        self.assertTrue(np.allclose(bounds[2.0], STEER_RATE_MAX * (1.0 / 2.0) / LENGTH), bounds[2.0][:3])

    def test_a2_rate_bound_elementwise_with_varying_spacing_speed_and_floor(self):
        """間隔・v_ref が waypoint ごとに違っても、各ステップの幅が delta_s[n]/max(v_ref[n], 1.0) に従う。下限 1.0 m/s も効く。"""
        rng = np.random.default_rng(0)
        spacings = rng.uniform(0.5, 1.5, 60)
        v_refs = rng.choice([0.5, 2.0, 5.0, 8.0], 60)           # 0.5 は MIN_V_FOR_DT=1.0 で床に当たる
        path = FakePath(spacings, v_refs)
        mpc, _ = make_mpc(path)
        mpc.get_control()
        s = FakeOSQP.setups[0]
        upper, lower = s["u"][-(N - 1):], s["l"][-(N - 1):]
        self.assertTrue(np.allclose(upper, expected_rate_bounds(path, 0)), upper[:4])
        self.assertTrue(np.array_equal(lower, -upper))
        self.assertTrue((upper > 0).all())

    # ---- (b) ウォームスタート ----
    def test_b1_second_call_updates_q_l_u_Ax_without_setup(self):
        """2回目は setup を呼ばず、update に q・l・u・Ax を渡す（曲率が変わる経路でもパターンは同じ）。"""
        kappas = 0.02 * np.sin(np.arange(60) / 3.0)
        path = FakePath([1.0] * 60, [5.0] * 60, kappas)
        mpc, _ = make_mpc(path)
        mpc.get_control()
        mpc.get_control()
        self.assertEqual(FakeOSQP.setup_calls, 1)
        self.assertEqual(FakeOSQP.update_calls, 1)
        upd = FakeOSQP.updates[0]
        for key in ("q", "l", "u", "Ax"):
            self.assertIn(key, upd)
        self.assertEqual(len(upd["u"]), n_bounds())
        self.assertTrue(np.allclose(upd["u"][-(N - 1):], expected_rate_bounds(path, 1)))   # 2回目は waypoint 1 から
        self.assertEqual(len(upd["Ax"]), FakeOSQP.setups[0]["A"].nnz)
        self.assertFalse(np.array_equal(upd["Ax"], FakeOSQP.setups[0]["A"].data))      # 曲率が違うので値は変わる

    def test_b2_changed_Q_passes_Px_and_changed_pattern_resetups(self):
        """Q を変えたら Px も渡す。ホライズン長が変わる（パターンが変わる）と setup し直す。"""
        mpc, car = make_mpc(uniform_path(5.0))
        mpc.get_control()
        mpc.update_Q(sparse.diags([2.0, 1.0, 1.0]))
        mpc.get_control()
        self.assertEqual(FakeOSQP.setup_calls, 1)
        self.assertIn("Px", FakeOSQP.updates[-1])
        # 周回しない短い経路（11 点）に差し替えると N が min(20, 11 - 0) = 11 に縮み、パターンが変わる
        short = FakePath([1.0] * 11, [5.0] * 11, circular=False)
        short.update_simple_path_constraints(11, car.safety_margin)
        car.reference_path = short
        car._calls = 0
        mpc.get_control()
        self.assertEqual(FakeOSQP.setup_calls, 2)
        self.assertEqual(len(FakeOSQP.setups[1]["u"]), NX * 12 + (NX * 12 + NU * 11) + 10)

    # ---- (c) 解の検証とフォールバック ----
    def _fallback_case(self, **reset_kwargs):
        mpc, _ = make_mpc(uniform_path(5.0))
        u_first, _ = mpc.get_control()
        FakeOSQP.reset(**reset_kwargs)               # 2回目以降の解を壊す（setup 回数の記録は消えるが使わない）
        FakeOSQP.setup_calls = 1
        u_second, _ = mpc.get_control()
        return mpc, u_first, u_second

    def _assert_fell_back_to_step1(self, mpc, u_first, u_second):
        self.assertTrue(np.all(np.isfinite(u_second)), u_second)
        self.assertAlmostEqual(u_second[0], 6.0)                                  # 前回予測の 2 ステップ目の速度 (5 + 1)
        # 2 ステップ目の舵角 arctan(0.02 L) = 0.0217 は、前回の舵角 0.00875 からレート上限 0.00875 しか動けない
        self.assertAlmostEqual(u_first[1], STEER_RATE_MAX * TS)
        self.assertAlmostEqual(u_second[1], u_first[1] + STEER_RATE_MAX * TS)
        self.assertAlmostEqual(mpc.previous_steering, u_second[1])
        self.assertEqual(mpc.stats.fallbacks, 1)
        self.assertEqual(mpc.stats.rejected, 6)                                   # 1 回 + 緩和 5 回

    def test_c1_nan_solution_falls_back_to_previous_input(self):
        """解に NaN があれば棄却し、前回の予測入力（2ステップ目）に切り替える。"""
        mpc, u_first, u_second = self._fallback_case(nan_from_solve=1)
        self.assertTrue(np.all(np.isfinite(u_first)))
        self._assert_fell_back_to_step1(mpc, u_first, u_second)

    def test_c2_unaccepted_status_falls_back(self):
        """OSQP のステータスが primal infeasible なら、解が有限でも棄却する。"""
        mpc, u_first, u_second = self._fallback_case(status="primal infeasible")
        self._assert_fell_back_to_step1(mpc, u_first, u_second)

    def test_c3_curvature_box_violation_falls_back(self):
        """曲率が箱制約の上限を 5% 超えて破っていれば棄却する。"""
        mpc, u_first, u_second = self._fallback_case(kappa_scale=1.2 * KAPPA_MAX / (0.01 * N))  # 最大ステップで 1.2 倍
        self._assert_fell_back_to_step1(mpc, u_first, u_second)

    def test_c4_small_violation_within_tolerance_is_accepted_and_projected(self):
        """上限の 3% 超えは受け入れ、舵角上限に投影する（レート制限は別途掛かる）。"""
        mpc, _ = make_mpc(uniform_path(5.0))
        FakeOSQP.reset(kappa_scale=1.03 * KAPPA_MAX / (0.01 * N))
        mpc.get_control()
        stats = getattr(mpc, "stats", None)
        self.assertIsNotNone(stats, "修正版の MPC には stats がある")
        self.assertEqual((stats.rejected, stats.fallbacks), (0, 0))

    # ---- (d) 疎行列の組み立て ----
    def test_d_sparse_constraint_matrix_equals_dense_reference(self):
        """固定パターンの疎行列が、a284274 式の密行列と同じ（曲率・間隔・速度が変わる経路で）。"""
        rng = np.random.default_rng(1)
        path = FakePath(rng.uniform(0.5, 1.5, 60), rng.uniform(2.0, 9.0, 60), 0.05 * rng.standard_normal(60))
        mpc, car = make_mpc(path)
        mpc.get_control()
        A = FakeOSQP.setups[0]["A"].toarray()
        ref = dense_reference_A(car, path, 0)
        self.assertEqual(A.shape, ref.shape)
        self.assertTrue(np.allclose(A, ref), np.abs(A - ref).max())


class RealOsqpSmokeTest(unittest.TestCase):
    def test_e_two_calls_with_real_osqp(self):
        """本物の osqp で 2 回解く: 出力が有限、setup は 1 回、2 回目は update（キーワードの食い違いがあればここで落ちる）。"""
        mpc, _ = make_mpc(uniform_path(5.0))
        u1, _ = mpc.get_control()
        u2, _ = mpc.get_control()
        self.assertTrue(np.all(np.isfinite(u1)) and np.all(np.isfinite(u2)), (u1, u2))
        stats = getattr(mpc, "stats", None)
        self.assertIsNotNone(stats, "修正版の MPC には stats がある")
        self.assertEqual(stats.setups, 1)
        self.assertEqual(stats.rejected, 0)


if __name__ == "__main__":
    unittest.main()
