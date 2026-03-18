from pathlib import Path
import cv2, numpy as np
from insightface.app import FaceAnalysis

pairs_dir = Path('pares agosto centaurus')
app = FaceAnalysis(name='auraface', root='.', providers=['CPUExecutionProvider'], allowed_modules=['detection','recognition'])
app.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640,640))

def iod_from_face(face):
    if not hasattr(face, 'kps') or face.kps is None or len(face.kps) < 2:
        return None
    le, re = face.kps[0], face.kps[1]
    return float(np.linalg.norm(np.array(le)-np.array(re)))

rows=[]
for p in pairs_dir.iterdir():
    if p.suffix.lower() not in {'.jpg','.jpeg','.png','.bmp','.webp','.tif','.tiff'}:
        continue
    img = cv2.imread(str(p))
    if img is None:
        continue
    faces = app.get(img)
    if not faces:
        rows.append((p.name, False, None))
        continue
    f = max(faces, key=lambda x:(x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]))
    iod = iod_from_face(f)
    rows.append((p.name, True, iod))

det = [r for r in rows if r[1] and r[2] is not None]
vals = np.array([r[2] for r in det], dtype=float) if det else np.array([])
print(f'total_images={len(rows)} detected_with_iod={len(vals)}')
if len(vals):
    for q in [1,5,10,25,50,75,90,95,99]:
        print(f'iod_p{q}={np.percentile(vals,q):.2f}')
    print(f'iod_min={vals.min():.2f} iod_max={vals.max():.2f} iod_mean={vals.mean():.2f}')
