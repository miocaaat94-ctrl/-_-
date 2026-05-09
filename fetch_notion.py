"""
fetch_notion.py
노션 페이지 블록을 읽어 콜레스테롤·혹 수치 테이블을 파싱하고
data.json 으로 저장합니다.
"""
import os, re, json, urllib.request, urllib.error

TOKEN   = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"].replace("-", "")

TOKEN = TOKEN.strip().encode('ascii', 'ignore').decode('ascii')

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def notion_get(path):
    req = urllib.request.Request(f"https://api.notion.com/v1{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def rich_text(cells):
    """리치텍스트 셀 배열 → 순수 문자열"""
    return "".join(t.get("plain_text", "") for t in cells)

def parse_number(s):
    """'62.8 ✅' 같은 문자열에서 숫자만 추출"""
    s = s.strip()
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else None

# ── 페이지 하위 블록 전체 가져오기 ───────────────────────────────
def get_all_blocks(block_id):
    blocks, cursor = [], None
    while True:
        url = f"/blocks/{block_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        resp = notion_get(url)
        blocks.extend(resp["results"])
        if not resp.get("has_more"):
            break
        cursor = resp["next_cursor"]
    return blocks

# ── 테이블 블록 → 2D 배열 ────────────────────────────────────────
def parse_table(table_block_id):
    rows = get_all_blocks(table_block_id)
    result = []
    for row in rows:
        if row["type"] != "table_row":
            continue
        cells = [rich_text(c) for c in row["table_row"]["cells"]]
        result.append(cells)
    return result

# ── 메인 파싱 ────────────────────────────────────────────────────
blocks = get_all_blocks(PAGE_ID)

data = {
    "cholesterol": [],   # [{period, hdl, ldl, total, tri, note}]
    "nodules": {
        "liver":  [],    # [{period, size_cm}]
        "breast": [],    # [{period, size_cm, result, note}]
    },
    "schedule": [],      # [{item, period}]
}

# 헤딩 텍스트로 현재 섹션 추적
current_section = None

for block in blocks:
    btype = block["type"]

    # 헤딩으로 섹션 판별
    if btype in ("heading_1", "heading_2", "heading_3"):
        text = rich_text(block[btype]["rich_text"]).lower()
        if "콜레스테롤" in text or "혈관" in text:
            current_section = "cholesterol"
        elif "간 혹" in text:
            current_section = "liver"
        elif "유방" in text:
            current_section = "breast"
        elif "검진" in text or "일정" in text:
            current_section = "schedule"

    # 테이블 파싱
    if btype == "table":
        rows = parse_table(block["id"])
        if not rows or len(rows) < 2:
            continue
        header = rows[0]

        if current_section == "cholesterol":
            # 행: 항목 | 기간1 | 기간2 ...
            periods = header[1:]
            item_map = {}
            for row in rows[1:]:
                key = row[0].strip().lower()
                vals = row[1:]
                if "hdl" in key:
                    item_map["hdl"] = vals
                elif "ldl" in key:
                    item_map["ldl"] = vals
                elif "총" in key:
                    item_map["total"] = vals
                elif "중성" in key:
                    item_map["tri"] = vals
                elif "비고" in key:
                    item_map["note"] = vals

            for i, period in enumerate(periods):
                entry = {"period": period.strip()}
                for k in ("hdl", "ldl", "total", "tri"):
                    raw = item_map.get(k, [""] * len(periods))
                    entry[k] = parse_number(raw[i]) if i < len(raw) else None
                entry["note"] = item_map.get("note", [""] * len(periods))[i] if i < len(item_map.get("note", [])) else ""
                if any(entry.get(k) is not None for k in ("hdl","ldl","total","tri")):
                    data["cholesterol"].append(entry)

        elif current_section == "liver":
            # 행: 항목 | 기간1 | 기간2
            periods = header[1:]
            for row in rows[1:]:
                if "크기" in row[0].lower():
                    for i, period in enumerate(periods):
                        val = parse_number(row[i+1]) if i+1 < len(row) else None
                        if val is not None:
                            data["nodules"]["liver"].append({"period": period.strip(), "size_cm": val})

        elif current_section == "breast":
            periods = header[1:]
            size_row = note_row = result_row = None
            for row in rows[1:]:
                k = row[0].strip().lower()
                if "크기" in k:
                    size_row = row[1:]
                elif "비고" in k:
                    note_row = row[1:]
                elif "판정" in k:
                    result_row = row[1:]
            for i, period in enumerate(periods):
                size = parse_number(size_row[i]) if size_row and i < len(size_row) else None
                data["nodules"]["breast"].append({
                    "period": period.strip(),
                    "size_cm": size,
                    "result": result_row[i].strip() if result_row and i < len(result_row) else "",
                    "note": note_row[i].strip() if note_row and i < len(note_row) else "",
                })

        elif current_section == "schedule":
            for row in rows[1:]:
                if len(row) >= 2:
                    data["schedule"].append({"item": row[0].strip(), "period": row[1].strip()})

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ data.json 저장 완료")
print(json.dumps(data, ensure_ascii=False, indent=2))
