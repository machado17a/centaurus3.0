"""
Pipeline limpo para estudo de acuracia do AuraFace em comparacao 1:1.

Objetivos:
1) Avaliar pares genuinos (doc x cam) de uma pasta de imagens.
2) Opcionalmente gerar pares impostores para estimar FAR e EER.
3) Fazer varredura de limiar para apoiar calibracao de threshold.

Formato esperado dos arquivos:
- <id>_doc.<ext>
- <id>_cam.<ext>

Exemplo de uso:
python pipeline_auraface_estudo.py \
  --pairs-dir "pares agosto centaurus" \
  --out-dir "estudo_auraface_out" \
  --det-thresh 0.50 \
  --det-size 640 640 \
  --verified-threshold 70 \
  --warning-threshold 65 \
  --generate-impostors
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import cv2
import numpy as np
from insightface.app import FaceAnalysis


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}


class ConsoleProgress:
    def __init__(self, total: int, title: str, width: int = 28, heartbeat_sec: float = 10.0) -> None:
        self.total = max(int(total), 1)
        self.title = title
        self.width = max(int(width), 10)
        self.heartbeat_sec = max(float(heartbeat_sec), 1.0)
        self.current = 0
        self.start_ts = time.perf_counter()
        self._last_render_ts = 0.0
        self._last_render_done = -1
        self._render_every_n = max(1, self.total // 200)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _elapsed(self) -> float:
        return time.perf_counter() - self.start_ts

    def _eta(self) -> float:
        if self.current <= 0:
            return math.inf
        speed = self.current / max(self._elapsed(), 1e-9)
        remain = max(self.total - self.current, 0)
        return remain / max(speed, 1e-9)

    @staticmethod
    def _fmt_seconds(seconds: float) -> str:
        if math.isinf(seconds):
            return "--:--"
        s = int(max(seconds, 0.0))
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _render_line(self, done: int) -> str:
        frac = min(max(done / self.total, 0.0), 1.0)
        filled = int(round(frac * self.width))
        bar = "#" * filled + "-" * (self.width - filled)
        pct = frac * 100.0
        elapsed = self._fmt_seconds(self._elapsed())
        eta = self._fmt_seconds(self._eta())
        return f"{self.title}: [{bar}] {done}/{self.total} {pct:6.2f}% elapsed={elapsed} eta={eta}"

    def start(self) -> None:
        print(self._render_line(0), end="\r", flush=True)

        def _heartbeat_loop() -> None:
            while not self._stop.wait(self.heartbeat_sec):
                with self._lock:
                    done = self.current
                    line = self._render_line(done)
                print()
                print(f"[heartbeat] {line}", flush=True)

        self._thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        self._thread.start()

    def update(self, done: int) -> None:
        with self._lock:
            self.current = min(max(int(done), 0), self.total)
            now = time.perf_counter()
            should_render = (
                self.current == self.total
                or self._last_render_done < 0
                or (self.current - self._last_render_done) >= self._render_every_n
                or (now - self._last_render_ts) >= 0.20
            )
            if not should_render:
                return
            line = self._render_line(self.current)
            self._last_render_done = self.current
            self._last_render_ts = now
        print(line, end="\r", flush=True)

    def finish(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.heartbeat_sec + 1.0)
        with self._lock:
            self.current = self.total
            line = self._render_line(self.current)
        print(line, flush=True)


@dataclass
class PairRecord:
    pair_id: str
    doc_path: Path
    cam_path: Path


@dataclass
class EvalRow:
    pair_id: str
    label: str  # genuine | impostor
    doc_path: str
    cam_path: str
    faces_doc: int
    faces_cam: int
    ok_doc: bool
    ok_cam: bool
    cosine: Optional[float]
    similarity_pct: Optional[float]
    status: str
    error: str
    elapsed_ms: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark limpo de AuraFace para pares 1:1")
    parser.add_argument("--pairs-dir", required=True, help="Pasta com arquivos *_doc e *_cam")
    parser.add_argument("--out-dir", default="estudo_auraface_out", help="Pasta de saida de relatorios")
    parser.add_argument("--model-name", default="auraface", help="Nome do pack de modelo do InsightFace")
    parser.add_argument("--model-root", default=".", help="Root para InsightFace (deve conter models/<model-name>)")
    parser.add_argument("--det-thresh", type=float, default=0.50, help="Threshold de deteccao (0-1)")
    parser.add_argument("--det-size", nargs=2, type=int, default=[640, 640], metavar=("W", "H"))
    parser.add_argument("--verified-threshold", type=float, default=70.0, help="Limiar de verificado em %%")
    parser.add_argument("--warning-threshold", type=float, default=65.0, help="Limiar de atencao em %%")
    parser.add_argument("--max-pairs", type=int, default=0, help="Limita quantidade de pares genuinos (0 = todos)")
    parser.add_argument("--generate-impostors", action="store_true", help="Gera pares impostores para FAR/EER")
    parser.add_argument("--seed", type=int, default=42, help="Seed para reproducibilidade")
    parser.add_argument("--sweep-min", type=float, default=50.0, help="Min do sweep de threshold (%)")
    parser.add_argument("--sweep-max", type=float, default=90.0, help="Max do sweep de threshold (%)")
    parser.add_argument("--sweep-step", type=float, default=0.5, help="Passo do sweep de threshold (%)")
    parser.add_argument("--heartbeat-sec", type=float, default=10.0, help="Intervalo do heartbeat de progresso")
    return parser.parse_args()


def load_pairs(pairs_dir: Path) -> List[PairRecord]:
    doc_map: dict[str, Path] = {}
    cam_map: dict[str, Path] = {}

    files = [p for p in pairs_dir.iterdir() if p.is_file()]
    scan_prog = ConsoleProgress(total=len(files), title="scan_arquivos")
    scan_prog.start()
    for idx, file_path in enumerate(files, start=1):
        if not file_path.is_file() or file_path.suffix.lower() not in IMAGE_EXTS:
            scan_prog.update(idx)
            continue
        stem = file_path.stem
        lower = stem.lower()
        if lower.endswith("_doc"):
            pair_id = stem[:-4]
            doc_map[pair_id] = file_path
        elif lower.endswith("_cam"):
            pair_id = stem[:-4]
            cam_map[pair_id] = file_path
        scan_prog.update(idx)
    scan_prog.finish()

    common_ids = sorted(set(doc_map).intersection(cam_map))
    return [PairRecord(pair_id=i, doc_path=doc_map[i], cam_path=cam_map[i]) for i in common_ids]


def build_app(model_name: str, model_root: str, det_thresh: float, det_size: Iterable[int]) -> FaceAnalysis:
    app = FaceAnalysis(
        name=model_name,
        root=model_root,
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition"],
    )
    det_size_tuple = (int(det_size[0]), int(det_size[1]))
    app.prepare(ctx_id=-1, det_thresh=float(det_thresh), det_size=det_size_tuple)
    return app


def best_embedding(app: FaceAnalysis, image_bgr: np.ndarray) -> tuple[Optional[np.ndarray], int]:
    faces = app.get(image_bgr)
    if not faces:
        return None, 0
    # Escolhe a maior face para reduzir erro quando ha multiplas deteccoes.
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return face.normed_embedding, len(faces)


def cosine_to_pct(cosine: float) -> float:
    return ((cosine + 1.0) / 2.0) * 100.0


def classify(similarity_pct: float, verified_threshold: float, warning_threshold: float) -> str:
    if similarity_pct > verified_threshold:
        return "Verificado"
    if similarity_pct >= warning_threshold:
        return "Atencao durante a captura"
    return "Chamar Policial Federal"


def evaluate_pair(
    app: FaceAnalysis,
    pair_id: str,
    doc_path: Path,
    cam_path: Path,
    label: str,
    verified_threshold: float,
    warning_threshold: float,
) -> EvalRow:
    t0 = time.perf_counter()
    row = EvalRow(
        pair_id=pair_id,
        label=label,
        doc_path=str(doc_path),
        cam_path=str(cam_path),
        faces_doc=0,
        faces_cam=0,
        ok_doc=False,
        ok_cam=False,
        cosine=None,
        similarity_pct=None,
        status="Erro",
        error="",
        elapsed_ms=0.0,
    )
    try:
        img_doc = cv2.imread(str(doc_path))
        img_cam = cv2.imread(str(cam_path))
        if img_doc is None:
            raise FileNotFoundError(f"Nao foi possivel abrir: {doc_path.name}")
        if img_cam is None:
            raise FileNotFoundError(f"Nao foi possivel abrir: {cam_path.name}")

        emb_doc, faces_doc = best_embedding(app, img_doc)
        emb_cam, faces_cam = best_embedding(app, img_cam)
        row.faces_doc = faces_doc
        row.faces_cam = faces_cam
        row.ok_doc = emb_doc is not None
        row.ok_cam = emb_cam is not None

        if emb_doc is None:
            raise ValueError("Sem face detectada na imagem doc")
        if emb_cam is None:
            raise ValueError("Sem face detectada na imagem cam")

        cosine = float(np.clip(np.dot(emb_doc, emb_cam), -1.0, 1.0))
        sim_pct = float(cosine_to_pct(cosine))
        row.cosine = cosine
        row.similarity_pct = sim_pct
        row.status = classify(sim_pct, verified_threshold, warning_threshold)

    except Exception as exc:
        row.error = str(exc)
    finally:
        row.elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return row


def generate_impostor_pairs(genuine_pairs: List[PairRecord], seed: int) -> List[tuple[str, Path, Path]]:
    if len(genuine_pairs) < 2:
        return []
    rng = random.Random(seed)
    cams = [p.cam_path for p in genuine_pairs]
    rng.shuffle(cams)

    impostors: List[tuple[str, Path, Path]] = []
    for idx, pair in enumerate(genuine_pairs):
        cam_other = cams[idx]
        if cam_other.stem.lower().startswith(pair.pair_id.lower()):
            cam_other = cams[(idx + 1) % len(cams)]
        impostors.append((f"imp_{pair.pair_id}", pair.doc_path, cam_other))
    return impostors


def confusion(rows: List[EvalRow], threshold: float) -> dict:
    tp = tn = fp = fn = 0
    for r in rows:
        if r.similarity_pct is None:
            continue
        pred_pos = r.similarity_pct > threshold
        gt_pos = (r.label == "genuine")
        if gt_pos and pred_pos:
            tp += 1
        elif (not gt_pos) and (not pred_pos):
            tn += 1
        elif (not gt_pos) and pred_pos:
            fp += 1
        else:
            fn += 1

    total = tp + tn + fp + fn
    acc = (tp + tn) / total if total else math.nan
    far = fp / (fp + tn) if (fp + tn) else math.nan
    frr = fn / (fn + tp) if (fn + tp) else math.nan
    tar = tp / (tp + fn) if (tp + fn) else math.nan
    return {
        "threshold": threshold,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "acc": acc,
        "far": far,
        "frr": frr,
        "tar": tar,
    }


def sweep_threshold(rows: List[EvalRow], t_min: float, t_max: float, t_step: float) -> List[dict]:
    points = []
    thresholds: List[float] = []
    t = t_min
    while t <= t_max + 1e-9:
        thresholds.append(t)
        t += t_step

    sweep_prog = ConsoleProgress(total=len(thresholds), title="sweep_threshold")
    sweep_prog.start()
    for idx, thr in enumerate(thresholds, start=1):
        points.append(confusion(rows, thr))
        sweep_prog.update(idx)
    sweep_prog.finish()

    return points


def nearest_eer(points: List[dict]) -> Optional[dict]:
    valid = [p for p in points if not math.isnan(p["far"]) and not math.isnan(p["frr"])]
    if not valid:
        return None
    best = min(valid, key=lambda p: abs(p["far"] - p["frr"]))
    eer = (best["far"] + best["frr"]) / 2.0
    return {
        "threshold": best["threshold"],
        "far": best["far"],
        "frr": best["frr"],
        "eer": eer,
    }


def save_rows_csv(rows: List[EvalRow], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "pair_id",
            "label",
            "doc_path",
            "cam_path",
            "faces_doc",
            "faces_cam",
            "ok_doc",
            "ok_cam",
            "cosine",
            "similarity_pct",
            "status",
            "error",
            "elapsed_ms",
        ])
        for r in rows:
            writer.writerow([
                r.pair_id,
                r.label,
                r.doc_path,
                r.cam_path,
                r.faces_doc,
                r.faces_cam,
                int(r.ok_doc),
                int(r.ok_cam),
                "" if r.cosine is None else f"{r.cosine:.6f}",
                "" if r.similarity_pct is None else f"{r.similarity_pct:.4f}",
                r.status,
                r.error,
                f"{r.elapsed_ms:.3f}",
            ])


def write_markdown_report(summary: dict, out_md: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Estudo AuraFace - Relatorio")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- model_name: {summary['setup']['model_name']}")
    lines.append(f"- det_thresh: {summary['setup']['det_thresh']}")
    lines.append(f"- det_size: {summary['setup']['det_size']}")
    lines.append(f"- verified_threshold: {summary['setup']['verified_threshold']}%")
    lines.append(f"- warning_threshold: {summary['setup']['warning_threshold']}%")
    lines.append("")
    lines.append("## Dataset")
    lines.append(f"- pares genuinos: {summary['dataset']['genuine_pairs']}")
    lines.append(f"- pares impostores: {summary['dataset']['impostor_pairs']}")
    lines.append(f"- amostras avaliadas: {summary['dataset']['evaluated_rows']}")
    lines.append("")
    lines.append("## Deteccao")
    lines.append(f"- taxa doc com face: {summary['detection']['doc_detection_rate']:.2f}%")
    lines.append(f"- taxa cam com face: {summary['detection']['cam_detection_rate']:.2f}%")
    lines.append(f"- taxa ambos detectados: {summary['detection']['both_detection_rate']:.2f}%")
    lines.append("")
    lines.append("## Threshold atual")
    cur = summary["threshold_current"]
    lines.append(f"- threshold: {cur['threshold']}%")
    lines.append(f"- acc: {cur['acc']*100:.2f}%" if not math.isnan(cur['acc']) else "- acc: n/a")
    lines.append(f"- FAR: {cur['far']*100:.2f}%" if not math.isnan(cur['far']) else "- FAR: n/a")
    lines.append(f"- FRR: {cur['frr']*100:.2f}%" if not math.isnan(cur['frr']) else "- FRR: n/a")
    lines.append("")
    eer = summary.get("eer")
    if eer:
        lines.append("## EER estimado")
        lines.append(f"- threshold aproximado: {eer['threshold']:.2f}%")
        lines.append(f"- EER: {eer['eer']*100:.2f}%")
        lines.append("")

    lines.append("## Nota")
    lines.append("- Se o sistema legado usava cos >= 0.4, isso equivale a similaridade >= 70%.")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    pairs_dir = Path(args.pairs_dir)
    out_dir = Path(args.out_dir)
    if not pairs_dir.is_dir():
        raise SystemExit(f"Pasta nao encontrada: {pairs_dir}")

    print("[1/5] Descobrindo pares genuinos...")
    genuine_pairs = load_pairs(pairs_dir)
    if args.max_pairs and args.max_pairs > 0:
        genuine_pairs = genuine_pairs[: args.max_pairs]
    if not genuine_pairs:
        raise SystemExit("Nenhum par *_doc/*_cam encontrado.")
    print(f"  -> pares genuinos: {len(genuine_pairs)}")

    print("[2/5] Inicializando AuraFace...")
    app = build_app(
        model_name=args.model_name,
        model_root=args.model_root,
        det_thresh=args.det_thresh,
        det_size=args.det_size,
    )

    print("[3/5] Avaliando pares genuinos...")
    rows: List[EvalRow] = []
    genuine_prog = ConsoleProgress(total=len(genuine_pairs), title="genuinos", heartbeat_sec=args.heartbeat_sec)
    genuine_prog.start()
    for idx, p in enumerate(genuine_pairs, start=1):
        rows.append(
            evaluate_pair(
                app,
                pair_id=p.pair_id,
                doc_path=p.doc_path,
                cam_path=p.cam_path,
                label="genuine",
                verified_threshold=args.verified_threshold,
                warning_threshold=args.warning_threshold,
            )
        )
        genuine_prog.update(idx)
    genuine_prog.finish()

    impostor_count = 0
    if args.generate_impostors:
        print("[4/5] Gerando e avaliando impostores...")
        impostors = generate_impostor_pairs(genuine_pairs, seed=args.seed)
        impostor_count = len(impostors)
        imp_prog = ConsoleProgress(total=len(impostors), title="impostores", heartbeat_sec=args.heartbeat_sec)
        imp_prog.start()
        for idx, (imp_id, doc_p, cam_p) in enumerate(impostors, start=1):
            rows.append(
                evaluate_pair(
                    app,
                    pair_id=imp_id,
                    doc_path=doc_p,
                    cam_path=cam_p,
                    label="impostor",
                    verified_threshold=args.verified_threshold,
                    warning_threshold=args.warning_threshold,
                )
            )
            imp_prog.update(idx)
        imp_prog.finish()

    print("[5/5] Consolidando metricas e salvando relatorios...")
    total = len(rows)
    both_ok = [r for r in rows if r.ok_doc and r.ok_cam]
    doc_ok = sum(1 for r in rows if r.ok_doc)
    cam_ok = sum(1 for r in rows if r.ok_cam)

    sweep_points = sweep_threshold(rows, args.sweep_min, args.sweep_max, args.sweep_step)
    current_point = confusion(rows, args.verified_threshold)
    eer_point = nearest_eer(sweep_points)

    raw_csv = out_dir / "raw_scores.csv"
    sweep_csv = out_dir / "threshold_sweep.csv"
    summary_json = out_dir / "summary.json"
    report_md = out_dir / "report.md"

    save_rows_csv(rows, raw_csv)
    with sweep_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["threshold", "tp", "tn", "fp", "fn", "acc", "far", "frr", "tar"])
        for p in sweep_points:
            writer.writerow([
                f"{p['threshold']:.2f}",
                p["tp"],
                p["tn"],
                p["fp"],
                p["fn"],
                "" if math.isnan(p["acc"]) else f"{p['acc']:.6f}",
                "" if math.isnan(p["far"]) else f"{p['far']:.6f}",
                "" if math.isnan(p["frr"]) else f"{p['frr']:.6f}",
                "" if math.isnan(p["tar"]) else f"{p['tar']:.6f}",
            ])

    summary = {
        "setup": {
            "model_name": args.model_name,
            "model_root": str(Path(args.model_root).resolve()),
            "det_thresh": args.det_thresh,
            "det_size": [int(args.det_size[0]), int(args.det_size[1])],
            "verified_threshold": args.verified_threshold,
            "warning_threshold": args.warning_threshold,
            "seed": args.seed,
        },
        "dataset": {
            "pairs_dir": str(pairs_dir.resolve()),
            "genuine_pairs": len(genuine_pairs),
            "impostor_pairs": impostor_count,
            "evaluated_rows": total,
        },
        "detection": {
            "doc_detection_rate": (doc_ok / total * 100.0) if total else 0.0,
            "cam_detection_rate": (cam_ok / total * 100.0) if total else 0.0,
            "both_detection_rate": (len(both_ok) / total * 100.0) if total else 0.0,
        },
        "threshold_current": current_point,
        "eer": eer_point,
        "artifacts": {
            "raw_scores_csv": str(raw_csv.resolve()),
            "threshold_sweep_csv": str(sweep_csv.resolve()),
            "report_md": str(report_md.resolve()),
        },
    }

    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown_report(summary, report_md)

    print("Concluido.")
    print(f"- raw scores: {raw_csv}")
    print(f"- sweep:      {sweep_csv}")
    print(f"- summary:    {summary_json}")
    print(f"- report:     {report_md}")


if __name__ == "__main__":
    main()
