from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ISSUES = ROOT / "issues"


def load_config() -> dict:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    local = ROOT / "config.local.yaml"  # git-ignored personal overrides
    if local.exists():
        _merge(cfg, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    return cfg


def _merge(base: dict, over: dict):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v


@dataclass(frozen=True)
class Issue:
    """One monthly issue, identified by the month it is *sent* (YYYY-MM).

    The reporting period is the previous calendar month: the October issue
    covers September's dashboard, release notes, meet-up and so on.
    """

    year: int
    month: int

    @classmethod
    def parse(cls, s: str | None) -> "Issue":
        if not s:
            t = date.today()
            return cls(t.year, t.month)
        m = re.fullmatch(r"(\d{4})-(\d{1,2})", s.strip())
        if not m:
            raise SystemExit(f"Issue must look like YYYY-MM, got {s!r}")
        return cls(int(m.group(1)), int(m.group(2)))

    @property
    def slug(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def dir(self) -> Path:
        return ISSUES / self.slug

    @property
    def content_path(self) -> Path:
        return self.dir / "content.yaml"

    @property
    def sources_dir(self) -> Path:
        return self.dir / "sources"

    @property
    def month_name(self) -> str:
        return calendar.month_name[self.month]

    @property
    def period_start(self) -> date:
        return date(self.prev_year, self.prev_month, 1)

    @property
    def period_end(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def prev_month(self) -> int:
        return 12 if self.month == 1 else self.month - 1

    @property
    def prev_year(self) -> int:
        return self.year - 1 if self.month == 1 else self.year

    @property
    def prev_month_name(self) -> str:
        return calendar.month_name[self.prev_month]
