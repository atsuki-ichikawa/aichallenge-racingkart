# 手で引いた線（CSV）を制御器の読み込み関数で読み、制御器がならした後の線が帯 [lb, ub] の内側かを出す。
# 計算は docs/racing_line_evidence/band_check_smoothed.py と同じ（制御器の Map・ReferencePath をそのまま使う）。読むだけ。
# コンテナ内でパッケージのディレクトリから実行する。ふつうは check_line.sh <csv> 経由。
import math
import sys

import numpy as np
import yaml
from multi_purpose_mpc_ros.core.map import Map
from multi_purpose_mpc_ros.core.reference_path import ReferencePath
from multi_purpose_mpc_ros.core.utils import load_ref_path

cfg = yaml.safe_load(open('config/config.yaml'))
c = cfg['reference_path']
csv_path = sys.argv[1] if len(sys.argv) > 1 else c['csv_path']
x, y, _, _ = load_ref_path(csv_path)
print('csv: %s  (load_ref_path ok; first point == last point: %s)'
      % (csv_path, math.hypot(x[0] - x[-1], y[0] - y[-1]) < 1e-6))
rp = ReferencePath(Map(cfg['map']['yaml_path']), x, y, c['resolution'], c['smoothing_distance'], c['max_width'], c['circular'])
sm = cfg['bicycle_model']['width'] / math.sqrt(2)  # same as BicycleModel._compute_safety_margin
ub = np.array([wp.ub for wp in rp.waypoints]) - sm  # same as update_simple_path_constraints
lb = np.array([wp.lb for wp in rp.waypoints]) + sm
collapsed = ub < lb
outside = ~collapsed & ((ub < 0) | (lb > 0))
print('csv points %d -> controller waypoints %d  (resolution %s, smoothing_distance %s, max_width %s)'
      % (len(x), rp.n_waypoints, c['resolution'], c['smoothing_distance'], c['max_width']))
print('margin taken from each wall [m]: %.3f' % sm)
print('waypoints where the band collapses (ub < lb, controller sets both to 0): %d' % collapsed.sum())
print('waypoints where the line is outside the band (ub < 0 or lb > 0): %d' % outside.sum())
print('room from the line to the band edge, left  (ub) [m]: min %.2f  median %.2f' % (ub.min(), np.median(ub)))
print('room from the line to the band edge, right (-lb) [m]: min %.2f  median %.2f' % ((-lb).min(), np.median(-lb)))
print('band width ub-lb [m]: min %.2f  median %.2f  max %.2f' % ((ub - lb).min(), np.median(ub - lb), (ub - lb).max()))
for i in np.flatnonzero(outside | collapsed)[:10]:
    print('  wp %d  x %.2f  y %.2f  lb %.2f  ub %.2f' % (i, rp.waypoints[i].x, rp.waypoints[i].y, lb[i], ub[i]))
