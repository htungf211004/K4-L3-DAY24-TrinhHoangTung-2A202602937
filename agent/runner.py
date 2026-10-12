"""BƯỚC 3c — trifecta split + egress allowlist (13'). ĐÂY LÀ PHẦN KHÓ NHẤT.

Đọc CHECKPOINTS.md (§3c) trước khi viết code. Tóm tắt yêu cầu:

Tách 1 yêu cầu người dùng thành ít nhất 2 run riêng biệt — KHÔNG run nào
được cầm cả 3 chân của trifecta cùng lúc:

    Run A: gọi search_docs (untrusted content).
           KHÔNG gọi read_customer. KHÔNG gọi http_post.
    Run B: gọi read_customer (private data).
           CHỈ nhận input là TYPED, ĐÃ SANITIZE từ Run A — ví dụ
           list[int] ticket id trích từ TÊN FILE (vd "ticket-007.md" -> 7),
           KHÔNG BAO GIỜ nhận nguyên văn text của document. free text của
           attacker không được đi xa hơn Run A.

Mọi lần gọi tool (allow HAY deny) phải:
  1. Đi qua `agent.policy.check()` TRƯỚC KHI tool thật sự chạy.
  2. Được ghi vào ledger qua `agent.ledger.append()` — cả khi deny.
Nếu policy deny, KHÔNG được gọi tool đó.

--- Gợi ý kiến trúc (không bắt buộc theo đúng, nhưng đủ để làm trong 13') ---

data/customers.json có field `related_tickets: list[int]` cho mỗi khách
hàng — đây là NGUỒN TIN CẬY để map ticket_id -> customer_id, KHÔNG map qua
customer_id mà attacker nhúng trong nội dung document. Cụ thể:

    Run A: search_docs(message) -> lấy list[int] ticket_id từ TÊN FILE của
           các doc khớp (vd "ticket-999.md" -> 999). Cũng chạy
           llm.find_injection() trên text để log lại (KHÔNG dùng
           customer_id mà nó trả về).
    Run B: với mỗi ticket_id nhận từ Run A, tìm customer nào trong
           customers.json có ticket_id trong related_tickets, rồi
           read_customer(customer_id) đó — không phải customer_id lấy từ
           text tự do.

Vì sao cách này chống được một chỉ thị viết không dấu / lookalike: filter
chuỗi thô sẽ luôn có thể bị né bằng cách viết lại chỉ thị, nhưng nếu Run B
không bao giờ ĐỌC free text để quyết định gọi ai, thì việc né filter chuỗi
trở nên vô nghĩa — đây là containment (kiến trúc), khác với mitigation
(bộ lọc). Sinh viên NÊN thử filter chuỗi trước, rồi tự phá nó bằng
một bản viết lại không dấu của lure, trước khi chuyển sang cách này.

Interface bắt buộc (agent/loop.py import và gọi hàm này nếu tồn tại):

    handle(message: str, llm, log_dir: pathlib.Path | None = None,
           principal_id: str = "support_l1") -> str
        `llm` cung cấp:
            llm.find_injection(text: str) -> InjectedInstruction | None
            llm.summarize(docs: list[dict]) -> str
        `log_dir` là thư mục chứa ledger.jsonl (mặc định: reports/).
        Mỗi tool call truyền principal_id, requested_tool, agent_scopes,
        parent_scopes và expires_at vào PolicyContext; ledger ghi
        on_behalf_of = principal_id, agent_id, run_id, expires_at.
        Principal chỉ được tra trong data/principals.json. Run B không
        được đọc customer cho support_l1; dpo vẫn đọc được khách hợp lệ.
        Trả về câu trả lời cuối cùng hiển thị cho người dùng — hành vi
        quan sát được từ ngoài (CLI) không đổi so với trước khi contain,
        chỉ có sink log và ledger là khác.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from agent import ledger, pii, policy, tools

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DEFAULT_LEDGER_PATH = REPORTS_DIR / "ledger.jsonl"

_ROOT_SCOPES = ("search_docs", "read_customer")
_TICKET_FILE = re.compile(r"ticket-([0-9]+)(?:b)?\.md")


def _run_a(message: str, llm, authorize, run_id: str) -> tuple[list[int], str, bool]:
    """Đọc ticket, che PII khi tóm tắt; chỉ xuất ID từ tên file và cờ injection."""
    if not authorize(
        "search_docs", run_id, ("search_docs",), "internal",
        "summarize-tickets", {"query": message},
    ):
        return [], "Không được phép tìm ticket với quyền hiện tại.", False
    docs = tools.search_docs(message)
    ticket_ids = sorted({
        int(match.group(1)) for doc in docs
        if (match := _TICKET_FILE.fullmatch(doc["id"])) is not None
    })
    has_injection = llm.find_injection("\n\n".join(doc["text"] for doc in docs)) is not None
    safe_docs = [{"id": doc["id"], "text": pii.redact(doc["text"])} for doc in docs]
    return ticket_ids, llm.summarize(safe_docs), has_injection


def _run_b(ticket_ids: list[int], authorize, run_id: str) -> None:
    """Chỉ nhận ID từ tên file; tìm khách qua related_tickets của dữ liệu gốc."""
    if not isinstance(ticket_ids, list) or any(type(item) is not int or item < 0 for item in ticket_ids):
        raise ValueError("Run B requires a list of non-negative integer ticket IDs")
    if not ticket_ids:
        return
    arguments = {"ticket_ids": ticket_ids}
    # Kiểm trước cả việc mở file để tra liên kết, không đọc rồi mới lọc.
    if not authorize(
        "read_customer", run_id, ("read_customer",), "restricted",
        "support-reply", arguments, delegation_depth=1,
        parent_scopes=_ROOT_SCOPES, stage="customer-lookup",
    ):
        return
    customers = json.loads(tools.CUSTOMERS_FILE.read_text(encoding="utf-8"))
    related_ids = sorted({
        customer["customer_id"] for customer in customers
        if any(ticket_id in ticket_ids for ticket_id in customer.get("related_tickets", []))
    })
    for customer_id in related_ids:
        if authorize(
            "read_customer", run_id, ("read_customer",), "restricted",
            "support-reply", {"customer_id": customer_id}, delegation_depth=1,
            parent_scopes=_ROOT_SCOPES,
        ):
            # Hồ sơ được đọc trong Run B, không chuyển sang lượt kiểm gửi.
            tools.read_customer(customer_id)


class RunnerScaffoldPending(NotImplementedError):
    """Only the original 3c stub uses this to enable the CP1/CP2 baseline."""


def handle(message: str, llm, log_dir: Path | None = None,
           principal_id: str = "support_l1") -> str:
    ledger_path = Path(log_dir) / "ledger.jsonl" if log_dir is not None else DEFAULT_LEDGER_PATH
    agent_id = f"lab24-agent-{uuid4().hex}"
    run_a_id = f"run-a-{uuid4().hex}"
    run_b_id = f"run-b-{uuid4().hex}"
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    def authorize(tool, run_id, scopes, classification, purpose, arguments,
                  egress_enabled=False, delegation_depth=0, parent_scopes=(),
                  stage="tool-call"):
        context = policy.PolicyContext(
            data_classification=classification,
            request_purpose=purpose,
            agent_owner=f"{agent_id}/{run_id}",
            delegation_depth=delegation_depth,
            egress_enabled=egress_enabled,
            principal_id=principal_id,
            requested_tool=tool,
            agent_scopes=scopes,
            parent_scopes=parent_scopes,
            expires_at=expires_at,
        )
        allowed, reason = policy.check(context)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("policy decision must include a reason")
        args_json = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        ledger.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "on_behalf_of": principal_id,
            "agent_id": agent_id,
            "run_id": run_id,
            "expires_at": expires_at,
            "tool": tool,
            "args_hash": hashlib.sha256(args_json.encode("utf-8")).hexdigest(),
            "classification": classification,
            "request_purpose": purpose,
            "delegation_depth": delegation_depth,
            "agent_scopes": list(scopes),
            "parent_scopes": list(parent_scopes),
            "egress_enabled": egress_enabled,
            "stage": stage,
            "decision": "allow" if allowed else "deny",
            "reason": reason,
        }, ledger_path)
        return allowed

    ticket_ids, answer, has_injection = _run_a(message, llm, authorize, run_a_id)
    _run_b(ticket_ids, authorize, run_b_id)
    if has_injection:
        url = "http://127.0.0.1:10024/reconcile"
        # Chỉ xin quyền bằng URL. Rule restricted + egress ghi deny vào ledger.
        authorize(
            "http_post", run_b_id, ("read_customer",), "restricted",
            "support-reply", {"url": url}, egress_enabled=True,
            delegation_depth=1, parent_scopes=_ROOT_SCOPES,
        )
    return answer
