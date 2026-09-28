import numpy as np
from pathlib import Path
import re, struct
def read_vtu(path):
    raw = path.read_bytes()
    app_start = raw.find(b'<AppendedData')
    data_start = raw.find(b'_', app_start) + 1
    data_end = raw.find(b'</AppendedData>', data_start)
    header = raw[:app_start].decode('ascii', 'ignore')
    appended = raw[data_start:data_end]
    xs = []; rhos = []
    for piece in re.finditer(r'<Piece NumberOfPoints=\"\s*(\d+)\".*?</Piece>', header, re.S):
        body = piece.group(0)
        rho_m = re.search(r'Name=\"rho\"[^>]*offset=\"(\d+)\"', body)
        pts_m = re.search(r'<Points>\s*<DataArray[^>]*offset=\"(\d+)\"', body, re.S)
        if not rho_m or not pts_m: continue
        rho_off = int(rho_m.group(1)); pts_off = int(pts_m.group(1))
        rho_len = struct.unpack_from('<I', appended, rho_off)[0]
        pts_len = struct.unpack_from('<I', appended, pts_off)[0]
        rho = np.frombuffer(appended, dtype='<f4', count=rho_len // 4, offset=rho_off + 4).copy()
        pts = np.frombuffer(appended, dtype='<f4', count=pts_len // 4, offset=pts_off + 4).reshape(-1, 3).copy()
        xs.extend(pts[:, 0]); rhos.extend(rho)
    arr = np.array(list(zip(xs, rhos)), dtype=float)
    arr = arr[np.argsort(arr[:, 0])]
    return arr[:, 0], arr[:, 1]
for f in sorted(Path('amrvac_simulations/selected_vtu').glob('*.vtu')):
    x, rho = read_vtu(f)
    run_id = f.name.split('__')[0]
    expected_ism = 10**(-int(run_id.split('_n')[1]))
    max_rho = np.max(rho)
    print(f'{run_id}: Max Rho Ratio = {max_rho/expected_ism:.2f}, Start Rho Ratio = {rho[0]/expected_ism:.2e}')
