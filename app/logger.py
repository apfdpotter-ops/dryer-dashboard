import csv
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import sensors


class CsvLogger:
    def __init__(self, log_dir: str, interval_seconds: int = 900):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.interval = int(interval_seconds)
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._current_file: Optional[Path] = None

    def _make_filename(self) -> Path:
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        return self.log_dir / f"dryer-log-{ts}.csv"

    def _write_header_if_needed(self, path: Path):
        if not path.exists():
            with path.open('w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'inlet_c', 'outlet_c', 'inlet_v', 'outlet_v',
                    'simulated', 'errors', 'auger_pct', 'bushels_per_hr'
                ])

    def _append_row(self, path: Path, row: list):
        # append safely (locking in-process)
        with self._lock:
            with path.open('a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

    def _sample_and_write(self, path: Path):
        # get sensor payload and computed fields
        try:
            payload = sensors.read_all() if hasattr(sensors, 'read_all') else {}
        except Exception:
            payload = {}

        inlet_c = payload.get('inlet_c')
        outlet_c = payload.get('outlet_c')
        inlet_v = payload.get('inlet_v')
        outlet_v = payload.get('outlet_v')
        simulated = bool(payload.get('simulated')) if isinstance(payload, dict) else False
        errors = payload.get('errors') if isinstance(payload, dict) else None
        auger = globals().get('_AUGER_PCT') if globals().get('_AUGER_PCT') is not None else ''
        # compute bushels same as app/data_for_ui: simple moisture->bushel
        def v_to_pct(v):
            try:
                pct = (float(v) / 3.3) * 100.0
                if pct < 0: pct = 0.0
                if pct > 100: pct = 100.0
                return pct
            except Exception:
                return None

        moisture_in = v_to_pct(inlet_v)
        if moisture_in is None:
            bushels = ''
        else:
            bushels = max(0.0, (1.0 - (moisture_in / 100.0)) * 100.0)

        row = [
            datetime.utcnow().isoformat() + 'Z',
            '' if inlet_c is None else inlet_c,
            '' if outlet_c is None else outlet_c,
            '' if inlet_v is None else inlet_v,
            '' if outlet_v is None else outlet_v,
            simulated,
            '' if errors is None else str(errors),
            auger,
            '' if bushels == '' else bushels,
        ]
        self._append_row(path, row)

    def _run(self):
        # create a file on start
        path = self._make_filename()
        self._write_header_if_needed(path)
        self._current_file = path

        # write an immediate sample
        try:
            self._sample_and_write(path)
        except Exception:
            pass

        while not self._stop.wait(self.interval):
            try:
                self._sample_and_write(path)
            except Exception:
                # swallow errors so thread keeps running
                pass

    def start(self):
        if self.is_running():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.is_running():
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def current_file(self) -> Optional[str]:
        return None if self._current_file is None else str(self._current_file.name)

    def list_logs(self):
        return sorted([p.name for p in self.log_dir.glob('dryer-log-*.csv')], reverse=True)

    def sample_once(self) -> Optional[str]:
        """Write a single sample to the current file (create one if needed).

        Returns the file name written to, or None on failure.
        """
        # Ensure there is a file to write to
        try:
            if self._current_file is None:
                path = self._make_filename()
                self._write_header_if_needed(path)
                self._current_file = path
            else:
                path = self._current_file

            # perform a single sample
            self._sample_and_write(path)
            return str(path.name)
        except Exception:
            return None

    def get_latest_row(self) -> Optional[str]:
        """Return the last non-empty CSV data row (not header) from the newest log file.

        Returns a string (CSV row) or None if no data available.
        """
        files = self.list_logs()
        if not files:
            return None

        newest = self.log_dir / files[0]
        try:
            with newest.open('r') as f:
                # read lines and skip blank lines
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            # header is first line; return last data row if present
            if len(lines) <= 1:
                return None
            return lines[-1]
        except Exception:
            return None


def create_logger(log_dir: str, interval_seconds: int = 900) -> CsvLogger:
    return CsvLogger(log_dir=log_dir, interval_seconds=interval_seconds)
