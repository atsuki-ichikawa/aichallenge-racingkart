#!/usr/bin/env python3
"""地図と今の線を data.js に埋め込む（line_editor.html が読む）。標準ライブラリだけ。

使い方: python3 make_data.py            （地図か線を差し替えたときだけ作り直す）
地図は 0（壁）と 255（走れる）だけの前提。制御器の Map.process_map は 5 マス未満の
壁の粒を消すが、この地図には無い（2026-11-17 に確認）。粒があればここで止まる。
"""
import base64
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(HERE, '../../workspace/src/aichallenge_submit/multi_purpose_mpc_ros/env/final_ver3')

meta = {}
for line in open(os.path.join(ENV, 'occupancy_grid_map.yaml')):
    if ':' in line:
        key = line.split(':')[0].strip()
        meta[key] = line.split(':', 1)[1].strip()
    elif line.strip().startswith('-'):
        meta.setdefault('origin_list', []).append(float(line.strip()[1:]))
raw = open(os.path.join(ENV, meta['image']), 'rb').read()
magic, size, maxval, cells = raw.split(b'\n', 3)
W, H = map(int, size.split())
assert magic == b'P5' and maxval == b'255' and len(cells) == W * H, (magic, maxval, len(cells))
assert set(cells) <= {0, 255}, sorted(set(cells))

# 1 マス 1 ビット（1 = 走れる）。行は画像の上から。
bits = bytearray((W * H + 7) // 8)
for i, v in enumerate(cells):
    if v:
        bits[i >> 3] |= 1 << (i & 7)

# config.yaml から読む値: 車幅（安全マージン込み）と、制御器が線を取り直すときの設定。帯の表示に使う。
cfg = open(os.path.join(ENV, '../../config/config.yaml')).read()


def cfg_value(section, key):
    return float(re.search(r'^%s:\n(?:[ \t]+.*\n|\n)*?[ \t]+%s:\s*([0-9.]+)' % (section, key), cfg, re.M).group(1))


width = cfg_value('bicycle_model', 'width')
assert re.search(r'^reference_path:\n(?:[ \t]+.*\n|\n)*?[ \t]+circular:\s*true', cfg, re.M), 'circular: true の前提'
band = {'res': cfg_value('reference_path', 'resolution'), 'smooth': int(cfg_value('reference_path', 'smoothing_distance')),
        'maxw': cfg_value('reference_path', 'max_width')}

data = {
    'W': W, 'H': H, 'res': float(meta['resolution']), 'width': width, 'band': band,
    'ox': meta['origin_list'][0], 'oy': meta['origin_list'][1],
    'free_bits_b64': base64.b64encode(bytes(bits)).decode(),
    'csv_name': 'env/final_ver3/traj_mincurv.csv',
    'csv': open(os.path.join(ENV, 'traj_mincurv.csv')).read(),
}
out = os.path.join(HERE, 'data.js')
with open(out, 'w') as f:
    f.write('// make_data.py が作った生成物。手で直さない。\nwindow.LINE_DATA = %s;\n' % json.dumps(data))
print('wrote %s  (map %dx%d, free cells %d, csv lines %d, width %s, band %s)'
      % (out, W, H, sum(1 for v in cells if v), data['csv'].count('\n'), width, band))
