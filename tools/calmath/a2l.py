"""A2L-driven decoding of calibration characteristics.

Everything (address, record layout, axis count, conversion) is taken from the A2L,
nothing is hard-coded per map. Supported: VALUE / CURVE / MAP with STD_AXIS and
RAT_FUNC conversions, big-endian (MPC562) storage.
"""
import json
import os
import re
import struct
import bisect

A2L_PATH = ('diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/'
            '03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l')
CACHE_PATH = 'diagnostic-review/math-engine/a2l-cache.json'

_TOKEN = re.compile(r'"(?:[^"\\]|\\.|"")*"|\S+')  # A2L escapes quotes as \" or ""
_DTYPE = {'SBYTE': 'b', 'UBYTE': 'B', 'SWORD': 'h', 'UWORD': 'H',
          'SLONG': 'i', 'ULONG': 'I', 'FLOAT32_IEEE': 'f'}


def _blocks(text, kind):
    for m in re.finditer(r'/begin\s+%s\b(.*?)/end\s+%s\b' % (kind, kind), text, re.S):
        body = m.group(1)
        # drop nested IF_DATA blocks, they carry no decoding information we use
        body = re.sub(r'/begin\s+IF_DATA.*?/end\s+IF_DATA', ' ', body, flags=re.S)
        yield body


def parse_a2l(path=A2L_PATH):
    text = open(path, encoding='cp1252', errors='replace').read()
    compu = {}
    for body in _blocks(text, 'COMPU_METHOD'):
        t = _TOKEN.findall(body)
        entry = {'type': t[2], 'unit': t[4].strip('"')}
        if 'COEFFS' in t:
            i = t.index('COEFFS')
            entry['coeffs'] = [float(x) for x in t[i + 1:i + 7]]
        compu[t[0]] = entry
    layouts = {}
    for m in re.finditer(r'/begin\s+RECORD_LAYOUT\s+(\S+)(.*?)/end\s+RECORD_LAYOUT', text, re.S):
        items = []
        for line in m.group(2).splitlines():
            t = line.split()
            if len(t) >= 3 and t[0] in ('NO_AXIS_PTS_X', 'NO_AXIS_PTS_Y', 'AXIS_PTS_X', 'AXIS_PTS_Y', 'FNC_VALUES'):
                items.append({'kind': t[0], 'pos': int(t[1]), 'dtype': t[2],
                              'order': t[3] if len(t) > 3 else None})
        layouts[m.group(1)] = sorted(items, key=lambda x: x['pos'])
    chars = {}
    for body in _blocks(text, 'CHARACTERISTIC'):
        axes_src = re.findall(r'/begin\s+AXIS_DESCR(.*?)/end\s+AXIS_DESCR', body, re.S)
        head = re.sub(r'/begin\s+AXIS_DESCR.*?/end\s+AXIS_DESCR', ' ', body, flags=re.S)
        t = _TOKEN.findall(head)
        c = {'name': t[0], 'desc': t[1].strip('"'), 'kind': t[2], 'address': int(t[3], 16),
             'layout': t[4], 'conversion': t[6], 'lower': float(t[7]), 'upper': float(t[8]), 'axes': []}
        for a in axes_src:
            at = _TOKEN.findall(a)
            c['axes'].append({'attr': at[0], 'input': at[1], 'conversion': at[2], 'max_points': int(at[3])})
        chars[c['name']] = c
    return {'compu': compu, 'layouts': layouts, 'characteristics': chars}


_DB = None


def db():
    global _DB
    if _DB is None:
        if os.path.exists(CACHE_PATH) and os.path.getmtime(CACHE_PATH) >= os.path.getmtime(A2L_PATH):
            with open(CACHE_PATH, encoding='utf-8') as f:
                _DB = json.load(f)
        else:
            _DB = parse_a2l()
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, 'w', encoding='utf-8') as f:
                json.dump(_DB, f)
    return _DB


def to_phys(raw, conv_name):
    """ASAM RAT_FUNC: raw = (a*x^2 + b*x + c) / (d*x^2 + e*x + f). Only the linear form is used here."""
    cm = db()['compu'][conv_name]
    if cm['type'] != 'RAT_FUNC':
        raise ValueError('unsupported COMPU_METHOD %s (%s)' % (conv_name, cm['type']))
    a, b, c, d, e, f = cm['coeffs']
    if a != 0 or d != 0 or e != 0:
        raise ValueError('non-linear RAT_FUNC %s not supported' % conv_name)
    return (raw * f - c) / b


def unit(conv_name):
    return db()['compu'][conv_name]['unit']


class Characteristic:
    def __init__(self, name, binary):
        c = db()['characteristics'][name]
        self.name, self.desc, self.kind, self.address = name, c['desc'], c['kind'], c['address']
        self.conversion, self.unit = c['conversion'], unit(c['conversion'])
        layout = db()['layouts'][c['layout']]
        off = c['address']
        n = {}
        raw_axes = {}
        values = None
        for item in layout:
            fmt = '>' + _DTYPE[item['dtype']]
            size = struct.calcsize(fmt)
            if item['kind'].startswith('NO_AXIS_PTS'):
                n[item['kind'][-1]] = struct.unpack_from(fmt, binary, off)[0]
                off += size
            elif item['kind'].startswith('AXIS_PTS'):
                k = item['kind'][-1]
                raw_axes[k] = struct.unpack_from('>%d%s' % (n[k], fmt[1:]), binary, off)
                off += size * n[k]
            else:
                count = n.get('X', 1) * n.get('Y', 1)
                values = struct.unpack_from('>%d%s' % (count, fmt[1:]), binary, off)
                off += size * count
        self.size = off - c['address']
        self.axes = []
        for k, ax in zip(('X', 'Y'), c['axes']):
            self.axes.append({'input': ax['input'], 'unit': unit(ax['conversion']),
                              'points': [to_phys(r, ax['conversion']) for r in raw_axes[k]]})
        phys = [to_phys(v, c['conversion']) for v in values]
        if self.kind == 'MAP':
            nx, ny = n['X'], n['Y']
            # COLUMN_DIR: values stored column by column -> grid[ix][iy] = raw[ix*ny + iy]
            self.grid = [phys[ix * ny:(ix + 1) * ny] for ix in range(nx)]
        elif self.kind == 'CURVE':
            self.values = phys
        else:
            self.value = phys[0]

    @property
    def x(self):
        return self.axes[0]['points']

    @property
    def y(self):
        return self.axes[1]['points']

    def lookup(self, x, y=None, y_policy='clamp'):
        """Bilinear interpolation. X is always clamped. Y beyond the last node follows y_policy:
        'clamp' holds the edge value, 'extrapolate' continues the last segment slope."""
        if self.kind == 'CURVE':
            return _interp(self.x, self.values, x, 'clamp')
        ix0, ix1, fx = _bracket(self.x, x)
        v0 = _interp(self.y, self.grid[ix0], y, y_policy)
        v1 = _interp(self.y, self.grid[ix1], y, y_policy)
        return v0 + (v1 - v0) * fx

    def inverse_y(self, x, value):
        """Solve lookup(x, y) == value for y along the Y axis (piecewise linear, requires monotone rows).
        Returns (y, status) where status is 'IN_RANGE', 'BELOW_AXIS' or 'ABOVE_AXIS'."""
        ys = self.y
        col = [self.lookup(x, yy) for yy in ys]
        if any(b < a for a, b in zip(col, col[1:])):
            raise ValueError('%s not monotone along Y at x=%s' % (self.name, x))
        if value < col[0]:
            return ys[0], 'BELOW_AXIS'
        if value > col[-1]:
            return ys[-1], 'ABOVE_AXIS'
        j = max(0, min(len(ys) - 2, bisect.bisect_right(col, value) - 1))
        if col[j + 1] == col[j]:
            return ys[j], 'IN_RANGE'
        return ys[j] + (ys[j + 1] - ys[j]) * (value - col[j]) / (col[j + 1] - col[j]), 'IN_RANGE'


def _bracket(nodes, x):
    if x <= nodes[0]:
        return 0, 0, 0.0
    if x >= nodes[-1]:
        return len(nodes) - 1, len(nodes) - 1, 0.0
    i = bisect.bisect_right(nodes, x) - 1
    return i, i + 1, (x - nodes[i]) / (nodes[i + 1] - nodes[i])


def _interp(nodes, vals, x, policy):
    if x > nodes[-1] and policy == 'extrapolate':
        return vals[-1] + (vals[-1] - vals[-2]) * (x - nodes[-1]) / (nodes[-1] - nodes[-2])
    i0, i1, f = _bracket(nodes, x)
    return vals[i0] + (vals[i1] - vals[i0]) * f


def load(name, binary):
    return Characteristic(name, binary)
