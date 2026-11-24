"""LibreOffice headless wrapper — REAL import / recalculation / PDF export.

Hard rule: never fake software execution.  Every operation:
  * runs the real `soffice` binary and records command, exit code, stdout/stderr;
  * asserts on real artifacts afterwards (output file exists, size > 0, and
    for PDFs the %PDF magic bytes);
  * when soffice is unavailable returns {"status": "unavailable", ...} with
    the limitation stated — never a simulated success.

Recalculation is real: a dedicated user profile sets
  /org.openoffice.Office.Calc/Formula/Load  OOXMLRecalcMode=0 / ODFRecalcMode=0
("always recalculate on load"), so converting through that profile recomputes
formulas instead of trusting cached values.  verify_computed() re-exports the
recalculated sheet to CSV and lets the caller assert the numbers — if the
recalc did not happen, the cached (wrong) values show up and the assertion
fails loudly.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys

RECALC_XCU = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry"
           xmlns:xs="http://www.w3.org/2001/XMLSchema">
 <item oor:path="/org.openoffice.Office.Calc/Formula/Load">
  <prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop>
 </item>
 <item oor:path="/org.openoffice.Office.Calc/Formula/Load">
  <prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop>
 </item>
</oor:items>
"""


class Soffice:
    def __init__(self, binary: str = None, timeout: int = 180):
        self.binary = binary if binary is not None else (shutil.which("soffice")
                                                         or shutil.which("libreoffice"))
        self.timeout = timeout

    # ------------------------------------------------------------- status
    def status(self) -> dict:
        if not self.binary or not os.path.exists(self.binary):
            return {"available": False, "status": "unavailable",
                    "reason": "soffice binary not found in PATH",
                    "limit": "import/recalculate/pdf-export steps cannot run in this "
                             "environment; results below cover deterministic bookkeeping only"}
        try:
            p = subprocess.run([self.binary, "--version"], capture_output=True,
                               text=True, timeout=30)
            ver = (p.stdout or p.stderr).strip()
        except Exception as exc:  # noqa: BLE001
            return {"available": False, "status": "unavailable",
                    "reason": f"soffice --version failed: {exc}"}
        return {"available": True, "status": "available", "binary": self.binary,
                "version": ver}

    # ------------------------------------------------------------- helpers
    def _profile(self, work_dir: str, recalc: bool) -> str:
        prof = os.path.join(work_dir, ".lo_profile_recalc" if recalc else ".lo_profile")
        os.makedirs(os.path.join(prof, "user"), exist_ok=True)
        if recalc:
            with open(os.path.join(prof, "user", "registrymodifications.xcu"), "w",
                      encoding="utf-8") as fh:
                fh.write(RECALC_XCU)
        return os.path.abspath(prof)

    def _run(self, argv: list) -> dict:
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout)
            return {"returncode": p.returncode, "stdout": p.stdout[-2000:],
                    "stderr": p.stderr[-2000:], "cmd": " ".join(argv)}
        except subprocess.TimeoutExpired:
            return {"returncode": None, "error": f"timeout after {self.timeout}s",
                    "cmd": " ".join(argv)}
        except Exception as exc:  # noqa: BLE001
            return {"returncode": None, "error": f"{type(exc).__name__}: {exc}",
                    "cmd": " ".join(argv)}

    def convert(self, src: str, to: str, out_dir: str, work_dir: str = None,
                recalc: bool = False) -> dict:
        """Real conversion.  Asserts: exit 0 AND output file exists with size>0."""
        st = self.status()
        if not st["available"]:
            return {"status": "unavailable", "operation": f"convert-to-{to}",
                    "src": src, "reason": st["reason"], "limit": st.get("limit", "")}
        if not os.path.exists(src):
            return {"status": "failed", "operation": f"convert-to-{to}", "src": src,
                    "reason": "input file does not exist"}
        os.makedirs(out_dir, exist_ok=True)
        work_dir = work_dir or out_dir
        prof = self._profile(work_dir, recalc)
        argv = [self.binary, "--headless", "--norestore", "--nolockcheck",
                f"-env:UserInstallation=file://{prof}",
                "--convert-to", to, "--outdir", os.path.abspath(out_dir),
                os.path.abspath(src)]
        run = self._run(argv)
        base = os.path.splitext(os.path.basename(src))[0]
        ext = {"pdf": ".pdf", "csv": ".csv", "xlsx": ".xlsx", "ods": ".ods",
               "fods": ".fods"}.get(to.split(":")[0], "." + to.split(":")[0])
        out_path = os.path.join(out_dir, base + ext)
        evidence = {"output_exists": os.path.exists(out_path),
                    "output_bytes": os.path.getsize(out_path) if os.path.exists(out_path) else 0}
        ok = run.get("returncode") == 0 and evidence["output_exists"] and evidence["output_bytes"] > 0
        if ok and to.split(":")[0] == "pdf":
            with open(out_path, "rb") as fh:
                evidence["pdf_magic"] = fh.read(5) == b"%PDF-"
            ok = ok and evidence["pdf_magic"]
        return {"status": "ok" if ok else "failed", "operation": f"convert-to-{to}",
                "src": src, "output": os.path.abspath(out_path) if evidence["output_exists"] else None,
                "soffice_version": st.get("version", ""), "run": run, "evidence": evidence,
                "recalc_profile": recalc,
                "reason": "" if ok else "exit code or artifact assertion failed"}

    # ------------------------------------------------- high-level chain
    def import_dataset(self, data_path: str, out_dir: str, work_dir: str,
                       to: str = "ods") -> dict:
        """导入: real import of a dataset file (csv/tsv/fods/xlsx) into a spreadsheet."""
        res = self.convert(data_path, to, out_dir, work_dir)
        res["operation"] = "import_dataset"
        return res

    def recalculate(self, sheet_path: str, out_dir: str, work_dir: str) -> dict:
        """重算: reload through the always-recalculate profile and save as xlsx."""
        res = self.convert(sheet_path, "xlsx", out_dir, work_dir, recalc=True)
        res["operation"] = "recalculate"
        return res

    def export_pdf(self, doc_path: str, out_dir: str, work_dir: str) -> dict:
        """导出: real PDF export with %PDF magic-byte verification."""
        res = self.convert(doc_path, "pdf", out_dir, work_dir)
        res["operation"] = "export_pdf"
        return res

    def verify_computed(self, sheet_path: str, out_dir: str, work_dir: str) -> dict:
        """复算检查: export the (recalculated) sheet to CSV and return the grid
        so callers can assert computed values against expectations."""
        res = self.convert(sheet_path, "csv:Text - txt - csv (StarCalc):44,34,76",
                           out_dir, work_dir, recalc=True)
        if res["status"] != "ok":
            res["operation"] = "verify_computed"
            return res
        rows = list(csv.reader(open(res["output"], encoding="utf-8", errors="replace")))
        res.update(operation="verify_computed", grid=rows)
        return res


FLAT_ODS_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<office:document
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2"
 office:version="1.2" office:mimetype="application/vnd.oasis.opendocument.spreadsheet">
 <office:body><office:spreadsheet>
  <table:table table:name="data">
   <table:table-row>
    <table:table-cell office:value-type="float" office:value="{a}"><text:p>{a}</text:p></table:table-cell>
    <table:table-cell office:value-type="float" office:value="{b}"><text:p>{b}</text:p></table:table-cell>
    <table:table-cell table:formula="of:=SUM([.A1:.B1])" office:value-type="float"
     office:value="{cached}"><text:p>{cached}</text:p></table:table-cell>
   </table:table-row>
  </table:table>
 </office:spreadsheet></office:body>
</office:document>
"""


def _demo() -> int:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="soffice-demo-")
    src = os.path.join(tmp, "dataset.fods")
    # cached value deliberately wrong (0): only a REAL recalculation yields a+b
    open(src, "w", encoding="utf-8").write(FLAT_ODS_TEMPLATE.format(a=2, b=3, cached=0))

    # 1) honest unavailable path — must report, never fake
    ghost = Soffice(binary="/nonexistent/soffice")
    g = ghost.export_pdf(src, os.path.join(tmp, "g"), tmp)
    assert g["status"] == "unavailable" and "not found" in g["reason"] or \
        g["status"] == "unavailable", g

    so = Soffice()
    st = so.status()
    if not st["available"]:
        # environment without LibreOffice: demo passes on the honest status
        assert st["status"] == "unavailable" and st["reason"]
        print(json.dumps({"demo": "soffice_ops", "environment": st["status"],
                          "reason": st["reason"],
                          "unavailable_path": "PASS"}, ensure_ascii=False))
        return 0

    # 2) import: real fods -> ods conversion, artifact asserted
    imp = so.import_dataset(src, os.path.join(tmp, "imported"), tmp)
    assert imp["status"] == "ok" and imp["evidence"]["output_bytes"] > 0, imp

    # 3) recalculate: cached 0 must become real 5
    rec = so.recalculate(imp["output"], os.path.join(tmp, "recalc"), tmp)
    assert rec["status"] == "ok", rec
    ver = so.verify_computed(rec["output"], os.path.join(tmp, "verify"), tmp)
    assert ver["status"] == "ok", ver
    row = ver["grid"][0]
    assert abs(float(row[2]) - 5.0) < 1e-9, f"recalc did not happen: {row}"

    # 4) PDF export: real file, real magic bytes
    pdf = so.export_pdf(rec["output"], os.path.join(tmp, "pdf"), tmp)
    assert pdf["status"] == "ok" and pdf["evidence"].get("pdf_magic"), pdf

    # 5) failure honesty: missing input must fail, not pretend
    miss = so.convert(os.path.join(tmp, "ghost.fods"), "pdf", os.path.join(tmp, "m"), tmp)
    assert miss["status"] == "failed"

    print(json.dumps({"demo": "soffice_ops import+recalc+pdf+verify",
                      "soffice": st["version"], "import_bytes": imp["evidence"]["output_bytes"],
                      "recalculated_value": row[2], "pdf_bytes": pdf["evidence"]["output_bytes"],
                      "unavailable_path": "PASS"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    so = Soffice()
    if cmd == "status":
        print(json.dumps(so.status(), ensure_ascii=False, indent=1))
    elif cmd == "convert":
        print(json.dumps(so.convert(sys.argv[2], sys.argv[3], sys.argv[4],
                                    sys.argv[5] if len(sys.argv) > 5 else None),
                         ensure_ascii=False, indent=1))
    elif cmd == "chain":  # import -> recalc -> pdf in one go
        src, out = sys.argv[2], sys.argv[3]
        imp = so.import_dataset(src, os.path.join(out, "imported"), out)
        res = {"import": imp}
        if imp["status"] == "ok":
            rec = so.recalculate(imp["output"], os.path.join(out, "recalc"), out)
            res["recalculate"] = rec
            if rec["status"] == "ok":
                res["verify"] = so.verify_computed(rec["output"], os.path.join(out, "verify"), out)
                res["pdf"] = so.export_pdf(rec["output"], os.path.join(out, "pdf"), out)
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print("usage: soffice_ops.py status | convert <src> <to> <outdir> [workdir] "
              "| chain <src> <outdir>")
        sys.exit(2)
