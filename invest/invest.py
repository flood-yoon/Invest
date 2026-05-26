#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NH나무증권 신용융자 포트폴리오 매수 계산기
  - 총 투자금액 = 순자산 × 2배 (신용융자 활용)
  - 신용 먼저 매수 → 잔여 현금으로 현금매수
  - 증거금률 30% / 40% 종목별 자동 반영
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[실행 전 설치]
  pip install yfinance

[실행 방법]
  python portfolio_calculator.py

[증거금률 변경]
  아래 PORTFOLIO 딕셔너리의 margin_rate 값을 수정하세요.
  0.40 = 40%,  0.30 = 30%
"""

# ─────────────────────────────────────────────────────────
#  포트폴리오 설정
#  yf_ticker        : Yahoo Finance 종목코드 (.KS=코스피, .KQ=코스닥)
#  allocation       : 비중 (합계 = 1.0)
#  margin_rate      : NH나무증권 신용융자 증거금률 (0.40 또는 0.30)
#  credit_available : 신용매수 가능 여부 (True/False)
#                     나무증권 앱에서 직접 확인 후 설정하세요
# ─────────────────────────────────────────────────────────
PORTFOLIO = {
    "삼성전자":   {"yf_ticker": "005930.KS", "allocation": 0.10, "margin_rate": 0.30, "credit_available": True},
    "SK하이닉스": {"yf_ticker": "000660.KS", "allocation": 0.10, "margin_rate": 0.30, "credit_available": True},
    "제룡전기":   {"yf_ticker": "236200.KQ", "allocation": 0.20, "margin_rate": 0.30, "credit_available": True},
    "코나아이":   {"yf_ticker": "052400.KQ", "allocation": 0.10, "margin_rate": 0.30, "credit_available": True},
    "GS리테일":   {"yf_ticker": "007070.KS", "allocation": 0.10, "margin_rate": 0.30, "credit_available": True},
    "원익피앤이": {"yf_ticker": "217820.KQ", "allocation": 0.20, "margin_rate": 0.40, "credit_available": False},  # 신용불가
    "하이브":     {"yf_ticker": "352820.KS", "allocation": 0.10, "margin_rate": 0.30, "credit_available": True},
    "한온시스템": {"yf_ticker": "018880.KS", "allocation": 0.10, "margin_rate": 0.30, "credit_available": True},
}

LEVERAGE = 2.0   # 총 투자금액 = 순자산 × LEVERAGE


# ─────────────────────────────────────────────────────────
#  주가 자동 조회 (yfinance)
# ─────────────────────────────────────────────────────────
def fetch_prices_auto() -> dict | None:
    """yfinance로 최근 종가 조회. 실패 시 None 반환."""
    try:
        import yfinance as yf
        prices = {}
        failed = []
        for name, info in PORTFOLIO.items():
            ticker_str = info["yf_ticker"]
            data = yf.Ticker(ticker_str)
            hist = data.history(period="5d")
            if not hist.empty and "Close" in hist.columns:
                prices[name] = int(hist["Close"].iloc[-1])
            else:
                # .KS 실패시 .KQ 재시도 (또는 반대)
                alt = ticker_str.replace(".KS", ".KQ") if ".KS" in ticker_str \
                      else ticker_str.replace(".KQ", ".KS")
                data2 = yf.Ticker(alt)
                hist2 = data2.history(period="5d")
                if not hist2.empty and "Close" in hist2.columns:
                    prices[name] = int(hist2["Close"].iloc[-1])
                else:
                    failed.append(name)

        if failed:
            print(f"  ⚠️  조회 실패 종목: {', '.join(failed)}")
            return None
        return prices

    except ImportError:
        print("  yfinance가 설치되지 않았습니다.")
        print("  → 터미널에서:  pip install yfinance  실행 후 다시 시도하세요.\n")
        return None
    except Exception as e:
        print(f"  조회 오류: {e}")
        return None


def input_prices_manual() -> dict:
    """사용자에게 현재가 직접 입력받기."""
    print("\n  현재 주가를 직접 입력해주세요 (단위: 원)")
    print("  " + "─" * 40)
    prices = {}
    for name in PORTFOLIO:
        while True:
            try:
                raw = input(f"  {name:<10} 현재가: ").replace(",", "").strip()
                val = int(raw)
                if val > 0:
                    prices[name] = val
                    break
                print("    0보다 큰 값을 입력해주세요.")
            except ValueError:
                print("    숫자를 입력해주세요.")
    return prices


# ─────────────────────────────────────────────────────────
#  핵심 계산 로직
# ─────────────────────────────────────────────────────────
def best_shares(target_won: float, price: int) -> int:
    """목표금액에 가장 가까운 주수 반환 (floor/ceil 중 선택)."""
    if price <= 0:
        return 0
    floor_n = int(target_won // price)
    ceil_n  = floor_n + 1
    diff_f  = abs(floor_n * price - target_won)
    diff_c  = abs(ceil_n  * price - target_won)
    return ceil_n if diff_c <= diff_f else floor_n


def calculate(net_assets_manwon: float, prices: dict) -> None:
    """포트폴리오 매수 계획 계산 및 출력."""

    net_assets   = net_assets_manwon * 10_000
    total_target = net_assets * LEVERAGE

    # ── 신용/현금 비율 계산 ──────────────────────────────────
    # 신용불가 종목 = 전액 현금 / 신용가능 종목 = credit_scale 비율만큼 신용
    #
    # [현금 균형 조건]
    #   credit_scale × credit_total × avg_margin
    #   + (1-credit_scale) × credit_total + nocredit_total = net_assets
    #
    # credit_scale > 1 → 2배 달성 불가 → total_target 줄이고 credit_scale=1 고정

    credit_alloc   = sum(v["allocation"] for v in PORTFOLIO.values() if     v["credit_available"])
    nocredit_alloc = sum(v["allocation"] for v in PORTFOLIO.values() if not v["credit_available"])

    weighted_margin = sum(
        v["allocation"] * v["margin_rate"]
        for v in PORTFOLIO.values() if v["credit_available"]
    )
    avg_margin = (weighted_margin / credit_alloc) if credit_alloc else 0

    raw_credit_scale = (
        (net_assets - total_target) / (total_target * credit_alloc * (avg_margin - 1))
        if (credit_alloc and avg_margin != 1) else 0
    )

    leverage_warning = None
    if raw_credit_scale > 1.0:
        # 2배 불가 → credit_scale=1, total_target을 현금이 딱 맞는 최대값으로 축소
        denom = credit_alloc * avg_margin + nocredit_alloc
        total_target = (net_assets / denom) if denom > 0 else total_target
        credit_scale = 1.0
        cash_scale   = 0.0
        actual_leverage = total_target / net_assets
        lv = int(LEVERAGE)
        leverage_warning = (
            "  WARNING: 신용불가 종목 비중이 커서 {}배 레버리지 달성 불가 -- "
            "현금 한도 내 최대 레버리지 {:.2f}배로 계산 -- "
            "신용불가 종목 비중 축소 또는 순자산 증가 시 {}배 가능"
        ).format(lv, actual_leverage, lv)
    else:
        credit_scale = raw_credit_scale
        cash_scale   = 1.0 - credit_scale

    # ── 종목별 계산 ─────────────────────────────────────────
    rows = []
    for name, info in PORTFOLIO.items():
        price      = prices[name]
        target     = total_target * info["allocation"]
        can_credit = info["credit_available"]

        if can_credit:
            cr_target   = target * credit_scale
            cash_target = target * cash_scale
        else:
            cr_target   = 0       # 신용불가 → 신용 0
            cash_target = target  # 전액 현금

        cr_shares   = best_shares(cr_target,   price)
        cash_shares = best_shares(cash_target, price)

        cr_won      = cr_shares   * price
        cash_won    = cash_shares * price
        margin_paid = cr_won * info["margin_rate"]
        loan_won    = cr_won * (1 - info["margin_rate"])

        rows.append({
            "name":           name,
            "credit_available": can_credit,
            "margin_rate": info["margin_rate"],
            "price":       price,
            "target":      target,
            "cr_shares":   cr_shares,
            "cash_shares": cash_shares,
            "cr_won":      cr_won,
            "cash_won":    cash_won,
            "margin_paid": margin_paid,
            "loan_won":    loan_won,
            "total_won":   cr_won + cash_won,
        })

    # ── 합계 ────────────────────────────────────────────────
    total_cr_won   = sum(r["cr_won"]      for r in rows)
    total_cash_won = sum(r["cash_won"]    for r in rows)
    total_margin   = sum(r["margin_paid"] for r in rows)
    total_loan     = sum(r["loan_won"]    for r in rows)
    total_invested = sum(r["total_won"]   for r in rows)
    cash_needed    = total_margin + total_cash_won

    def mw(won): return won / 10_000

    W  = 66
    DV = "─" * W
    DV2= "━" * W

    print()
    print(DV2)
    print("  💰 NH나무증권 신용융자 포트폴리오 매수 계획")
    print(DV2)
    print(f"  순자산       : {net_assets_manwon:>10,.0f} 만원")
    print(f"  총 투자목표  : {mw(total_target):>10,.0f} 만원  (×{LEVERAGE:.0f}배)")
    print(f"  신용 비율    : {credit_scale*100:.1f}%   현금 비율: {cash_scale*100:.1f}%")
    if leverage_warning:
        print()
        print(leverage_warning)
    print()

    # ──── 1단계: 신용매수 ────
    print(DV)
    print("  【 1단계 】 신용매수  ← 반드시 먼저 체결")
    print(DV)
    print(f"  {'종목':<10} {'현재가':>9} {'신용':>5} {'매수금액':>9} {'증거금':>9} {'융자금':>9}")
    print(f"  {'':─<10} {'':─>9} {'':─>5} {'':─>9} {'':─>9} {'':─>9}")
    for r in rows:
        mg = f"({int(r['margin_rate']*100)}%)"
        if not r["credit_available"]:
            print(f"  {r['name']:<10} {r['price']:>8,}원    ─  {'⛔신용불가':>10}")
        elif r["cr_shares"] > 0:
            print(f"  {r['name']:<10} {r['price']:>8,}원 {r['cr_shares']:>4}주 "
                  f"{mw(r['cr_won']):>8,.1f}만 "
                  f"{mw(r['margin_paid']):>7,.1f}만{mg} "
                  f"{mw(r['loan_won']):>8,.1f}만")
        else:
            print(f"  {r['name']:<10} {r['price']:>8,}원    ─  {'신용없음':>9}")
    print(f"  {'합계':-<10} {'':->9} {'':->5} "
          f"{mw(total_cr_won):>8,.1f}만 "
          f"{mw(total_margin):>9,.1f}만 "
          f"{mw(total_loan):>8,.1f}만")
    print()

    # ──── 2단계: 현금매수 ────
    print(DV)
    print("  【 2단계 】 현금매수  ← 신용매수 완료 후 진행")
    print(DV)
    print(f"  {'종목':<10} {'현재가':>9} {'현금':>5} {'매수금액':>9}")
    print(f"  {'':─<10} {'':─>9} {'':─>5} {'':─>9}")
    for r in rows:
        if r["cash_shares"] > 0:
            print(f"  {r['name']:<10} {r['price']:>8,}원 {r['cash_shares']:>4}주 "
                  f"{mw(r['cash_won']):>8,.1f}만")
        else:
            print(f"  {r['name']:<10} {r['price']:>8,}원    ─  {'현금없음':>9}")
    print(f"  {'합계':-<10} {'':->9} {'':->5} {mw(total_cash_won):>8,.1f}만")
    print()

    # ──── 종목별 요약 ────
    print(DV)
    print("  📊 종목별 최종 요약")
    print(DV)
    print(f"  {'종목':<10} {'목표':>8} {'실제':>8} {'오차':>6} "
          f"{'신용':>5} {'현금':>5} {'합계':>5}  주가")
    print(f"  {'':─<10} {'':─>8} {'':─>8} {'':─>6} "
          f"{'':─>5} {'':─>5} {'':─>5}  {'':─>10}")
    for r in rows:
        dp = (r["total_won"] - r["target"]) / r["target"] * 100 if r["target"] else 0
        sg = "+" if dp >= 0 else ""
        ts = r["cr_shares"] + r["cash_shares"]
        cr_label = "불가" if not r["credit_available"] else f"{r['cr_shares']:>4}주"
        print(f"  {r['name']:<10} {mw(r['target']):>7,.0f}만 {mw(r['total_won']):>7,.0f}만 "
              f"{sg}{dp:>4.1f}% "
              f"{cr_label:>5} {r['cash_shares']:>4}주 {ts:>4}주  "
              f"{r['price']:,}원")
    print()

    # ──── 현금 흐름 ────
    print(DV2)
    print("  💵 현금 흐름 요약")
    print(DV2)
    print(f"  보유 순자산       : {net_assets_manwon:>10,.1f} 만원")
    print(f"  - 신용증거금 납입 : {mw(total_margin):>10,.1f} 만원")
    print(f"  - 현금매수 사용   : {mw(total_cash_won):>10,.1f} 만원")
    print(f"  {'':─<34}")
    print(f"  필요 현금 합계    : {mw(cash_needed):>10,.1f} 만원")
    surplus = net_assets - cash_needed
    if surplus >= 0:
        print(f"  잔여 현금         : {mw(surplus):>10,.1f} 만원  ✅")
    else:
        print(f"  현금 부족         : {mw(-surplus):>10,.1f} 만원  ⚠️")
    print()
    print(f"  총 투자금액 (실제): {mw(total_invested):>10,.1f} 만원")
    print(f"  └ 신용융자 (대출) : {mw(total_loan):>10,.1f} 만원")
    print(f"  └ 자기자본 투입   : {mw(cash_needed):>10,.1f} 만원")
    lev = total_invested / net_assets if net_assets else 0
    print(f"  실제 레버리지     : {lev:>10.2f} 배")
    print(DV2)
    print()


# ─────────────────────────────────────────────────────────
#  메인
# ─────────────────────────────────────────────────────────
def main():
    print()
    print("━" * 66)
    print("   📈  NH나무증권 신용융자 포트폴리오 계산기")
    print("━" * 66)

    # 1) 순자산 입력
    while True:
        try:
            raw = input("\n  보유 자산을 입력해 주세요. 단위 만원\n  입력값 : ") \
                  .replace(",", "").strip()
            net_assets_manwon = float(raw)
            if net_assets_manwon > 0:
                break
            print("  0보다 큰 값을 입력해주세요.")
        except ValueError:
            print("  숫자를 입력해주세요.")

    # 2) 주가 조회
    print("\n  주가 자동 조회 중... (Yahoo Finance)")
    prices = fetch_prices_auto()

    if prices:
        print("  ✅ 자동 조회 성공!")
        print("\n  " + "─" * 40)
        for name, price in prices.items():
            print(f"  {name:<10}: {price:>10,} 원")
        print()
        while True:
            ans = input("  이 주가로 계산할까요? (y/n) : ").strip().lower()
            if ans in ("y", "yes", ""):
                break
            if ans in ("n", "no"):
                prices = input_prices_manual()
                break
    else:
        print("  ⚠️  자동 조회 실패. 현재가를 직접 입력해주세요.")
        prices = input_prices_manual()

    # 3) 계산 출력
    calculate(net_assets_manwon, prices)

    # 4) 재계산
    while True:
        again = input("  다른 금액으로 재계산할까요? (y/n) : ").strip().lower()
        if again in ("n", "no", ""):
            print("\n  계산기를 종료합니다. 성공적인 투자 되세요! 📈\n")
            break
        if again in ("y", "yes"):
            while True:
                try:
                    raw = input("  새 보유 자산 (만원) : ").replace(",", "").strip()
                    new_assets = float(raw)
                    if new_assets > 0:
                        break
                except ValueError:
                    pass
                print("  숫자를 입력해주세요.")
            chg = input("  주가도 다시 입력할까요? (y/n) : ").strip().lower()
            if chg in ("y", "yes"):
                prices = input_prices_manual()
            calculate(new_assets, prices)


if __name__ == "__main__":
    main()