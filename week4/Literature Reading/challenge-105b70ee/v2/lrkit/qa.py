"""Question-answering bookkeeping: 逐题回答，也给出依据。

对应"文献智能问答"类任务的输出契约：
  answers[]: {question_id, answer, conditions[], status,
              claims[]: {claim_id, text, kind: reported|inferred,
                         evidence[]: {source, loc, quote}},
              unanswered_parts[]}
  coverage: 已读/未读章节及原因

引擎只做可复算的部分：
  - 状态合法性与字段齐备校验（不得省略无法回答的问题）
  - 每条 claim 的证据引用逐字核验（调 locate.verify_quote）
  - 答案文本不得出现材料中不存在的数字（轻量防幻觉检查）
  - 拒答/部分回答也必须成项，统计 coverage
"""
from __future__ import annotations

import json
import re
import sys

from . import locate

VALID_STATUS = {"answered", "partial", "insufficient_evidence", "input_error"}
VALID_KIND = {"reported", "inferred"}

_NUM = re.compile(r"\d+(?:\.\d+)?")


def _numbers(s: str) -> set[str]:
    return set(_NUM.findall(s or ""))


def _corpus_numbers(blocks: list[dict]) -> set[str]:
    out = set()
    for b in blocks:
        out |= _numbers(b.get("text", ""))
    return out


def validate_answer(answer: dict, blocks: list[dict]) -> dict:
    problems = []
    qid = answer.get("question_id") or answer.get("id") or "?"
    status = str(answer.get("status", ""))
    if status not in VALID_STATUS:
        problems.append(f"invalid status '{status}'")
    claims = answer.get("claims") or []
    if status == "answered" and not claims:
        problems.append("status=answered but no claims with evidence")
    if status in ("answered", "partial") and not (answer.get("answer") or "").strip():
        problems.append("answer text empty while status requires one")
    for cl in claims:
        cid = cl.get("claim_id", "?")
        if str(cl.get("kind", "")) not in VALID_KIND:
            problems.append(f"claim {cid}: invalid kind (reported|inferred)")
        evs = cl.get("evidence") or []
        if str(cl.get("kind", "reported")) == "reported" and not evs:
            problems.append(f"claim {cid}: reported claim without evidence")
        for ev in evs:
            r = locate.verify_quote(blocks, str(ev.get("loc", "")), ev.get("quote", ""))
            if not r["verified"]:
                problems.append(f"claim {cid}: evidence unverified ({r['reason']})")
    if status == "partial" and not answer.get("unanswered_parts"):
        problems.append("status=partial but unanswered_parts empty")
    # 数字保守检查：答案/条件里的每个数字应能在材料中找到
    if blocks:
        corpus = _corpus_numbers(blocks)
        for text, where in ((answer.get("answer", ""), "answer"),
                            (" ".join(answer.get("conditions") or []), "conditions")):
            for n in _numbers(text) - corpus:
                problems.append(f"number {n} in {where} not found in materials")
    return {"question_id": qid, "status": status, "problems": problems,
            "ok": not problems}


def validate_answers(questions: list[str], answers: list[dict],
                     blocks: list[dict]) -> dict:
    """questions: 全部 question_id；answers 必须一题不落。"""
    seen = {str(a.get("question_id") or a.get("id")) for a in answers}
    results = [validate_answer(a, blocks) for a in answers]
    missing = [q for q in questions if str(q) not in seen]
    problems = [{"question_id": q, "problem": "question omitted"} for q in missing]
    n_bad = sum(1 for r in results if not r["ok"])
    return {"per_answer": results, "missing": missing,
            "counts": {s: sum(1 for a in answers if a.get("status") == s) for s in VALID_STATUS},
            "n_questions": len(questions), "n_answers": len(answers),
            "omission_problems": problems,
            "ok": not missing and n_bad == 0,
            "rule": "every question must appear, even when unanswered; "
                    "claims need verbatim evidence; numbers must exist in materials"}


def build_answer_item(question_id: str, answer: str, status: str,
                      claims: list[dict] | None = None,
                      conditions: list[str] | None = None,
                      unanswered_parts: list[dict] | None = None) -> dict:
    """构造一条标准 answer 项（供 SKILL 工作流中拼装 JSON 用）。"""
    return {"question_id": question_id, "answer": answer, "status": status,
            "conditions": conditions or [], "claims": claims or [],
            "unanswered_parts": unanswered_parts or []}


def _demo() -> int:
    blocks = [
        {"loc": "P3", "source": "S1", "text": "The band gap is 1.62 eV, measured by "
         "UV-Vis spectroscopy at room temperature."},
        {"loc": "P7", "source": "S1", "text": "Photocatalytic degradation reached 92% "
         "within 60 min under visible light."},
    ]
    questions = ["Q1", "Q2", "Q3"]
    answers = [
        build_answer_item("Q1", "带隙为 1.62 eV。", "answered",
                          claims=[{"claim_id": "Q1-c1", "text": "band gap = 1.62 eV",
                                   "kind": "reported",
                                   "evidence": [{"source": "S1", "loc": "P3",
                                                 "quote": "The band gap is 1.62 eV"}]}],
                          conditions=["室温", "UV-Vis 测量"]),
        build_answer_item("Q2", "可见光下 60 min 降解 92%。", "answered",
                          claims=[{"claim_id": "Q2-c1", "text": "degradation 92% in 60 min",
                                   "kind": "reported",
                                   "evidence": [{"source": "S1", "loc": "P7",
                                                 "quote": "reached 92% within 60 min"}]}]),
        build_answer_item("Q3", "", "insufficient_evidence",
                          unanswered_parts=[{"part": "循环稳定性", "reason": "材料未报告"}]),
    ]
    rep = validate_answers(questions, answers, blocks)
    assert rep["ok"] and rep["counts"]["insufficient_evidence"] == 1, rep
    # 反例：编造数字 + 伪引文必须被抓出
    bad = [build_answer_item("Q1", "带隙为 1.85 eV。", "answered",
                             claims=[{"claim_id": "Q1-c1", "text": "x", "kind": "reported",
                                      "evidence": [{"loc": "P3", "quote": "1.85 eV"}]}])]
    rep2 = validate_answers(["Q1"], bad, blocks)
    assert not rep2["ok"] and len(rep2["per_answer"][0]["problems"]) >= 2
    print(json.dumps({"demo": "qa", "ok": rep["ok"], "counts": rep["counts"],
                      "fabrication_caught": not rep2["ok"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    questions = json.load(open(sys.argv[1], encoding="utf-8"))
    answers = json.load(open(sys.argv[2], encoding="utf-8"))
    blocks = json.load(open(sys.argv[3], encoding="utf-8"))
    rep = validate_answers(questions.get("questions", questions),
                           answers.get("answers", answers),
                           blocks.get("blocks", blocks))
    if len(sys.argv) > 4:
        json.dump(rep, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ok={rep['ok']} missing={len(rep['missing'])} "
          f"bad={sum(1 for r in rep['per_answer'] if not r['ok'])}")
    sys.exit(0 if rep["ok"] else 1)
