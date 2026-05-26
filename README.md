# 📈 NH나무증권 신용융자 포트폴리오 계산기
**NH Namu Securities Margin Loan Portfolio Calculator**

순자산을 입력하면 신용융자를 포함한 종목별 매수 수량과 순서를 자동으로 계산해주는 도구입니다.  
A tool that automatically calculates the number of shares to buy per stock, including margin loans, based on your net assets.

---

## ✨ 주요 기능 / Features

- 순자산 기준 **2배 레버리지** 자동 계산 / Auto 2x leverage calculation based on net assets
- **신용매수 → 현금매수** 순서 안내 / Buy order guidance: margin first, then cash
- 종목별 증거금률(30% / 40%) 반영 / Per-stock margin rate support (30% / 40%)
- **신용불가 종목** 수동 지정 및 현금매수 전환 / self-detection of credit-unavailable stocks
- 2배 달성 불가 시 최대 가능 레버리지로 자동 조정 및 경고 / Auto-adjusts to max achievable leverage with warning
- Yahoo Finance를 통한 **실시간 주가 자동 조회** (실패 시 수동 입력) / Real-time price fetch via Yahoo Finance (falls back to manual input)
- 주수 반올림 시 목표금액에 더 가까운 쪽 자동 선택 / Smart share rounding to closest target amount

---

## ⚙️ 설치 / Installation

Python 3.10 이상이 필요합니다. / Requires Python 3.10+.

```bash
pip install yfinance
```

---

## 🚀 실행 / Usage

```bash
python portfolio_calculator.py
```

실행 후 순자산(만원 단위)을 입력하면 됩니다.  
After running, enter your net assets in units of 10,000 KRW (만원).

```
보유 자산을 입력해 주세요. 단위 만원
입력값 : 1000
```

---

## 📋 출력 예시 / Output Example

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  💰 NH나무증권 신용융자 포트폴리오 매수 계획
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  순자산       :      1,000 만원
  총 투자목표  :      2,000 만원  (×2배)

──────────────────────────────────────────────────────────────────
  【 1단계 】 신용매수  ← 반드시 먼저 체결
──────────────────────────────────────────────────────────────────
  삼성전자    53,000원   31주   164.3만   65.7만(40%)   98.6만
  원익피앤이   5,000원    ─      ⛔신용불가

──────────────────────────────────────────────────────────────────
  【 2단계 】 현금매수  ← 신용매수 완료 후 진행
──────────────────────────────────────────────────────────────────
  삼성전자    53,000원    6주    31.8만
  원익피앤이   5,000원  800주   400.0만
```

---

## 🛠️ 포트폴리오 설정 / Portfolio Configuration

`portfolio_calculator.py` 상단의 `PORTFOLIO` 딕셔너리를 수정하세요.  
Edit the `PORTFOLIO` dictionary at the top of `portfolio_calculator.py`.

```python
PORTFOLIO = {
    "삼성전자":   {"yf_ticker": "005930.KS", "allocation": 0.10, "margin_rate": 0.40, "credit_available": True},
    "원익피앤이": {"yf_ticker": "217820.KQ", "allocation": 0.20, "margin_rate": 0.40, "credit_available": False},
    # ...
}
```

| 항목 / Field | 설명 / Description |
|---|---|
| `yf_ticker` | Yahoo Finance 종목코드. 코스피 `.KS`, 코스닥 `.KQ` / Yahoo Finance ticker. KOSPI: `.KS`, KOSDAQ: `.KQ` |
| `allocation` | 비중 (전체 합계 = 1.0) / Weight (total must equal 1.0) |
| `margin_rate` | 신용융자 증거금률. `0.40` = 40%, `0.30` = 30% / Margin deposit rate |
| `credit_available` | 신용매수 가능 여부. `True` / `False` / Whether margin buying is available |

레버리지 배수 변경 / To change leverage multiplier:
```python
LEVERAGE = 2.0  # 원하는 배수로 변경 / Change to desired multiplier
```

---

## ⚠️ 주의사항 / Notes

- **증거금률(margin_rate)** 은 야후 파이낸스에서 제공하지 않습니다. 나무증권 앱 또는 홈페이지 `신용융자 증거금률 조회` 메뉴에서 직접 확인 후 설정하세요.  
  `margin_rate` is not available from Yahoo Finance. Check it manually in the Namu Securities app or website under the margin rate inquiry menu.

- **신용가능 여부(credit_available)** 도 야후 파이낸스에서 제공하지 않습니다. 나무증권 앱에서 종목별로 직접 확인하세요.  
  `credit_available` is also not available from Yahoo Finance. Check each stock manually in the Namu Securities app.

- 이 계산기는 나무증권과 직접 연동되지 않습니다. 계산 결과를 참고하여 **직접 주문**하세요.  
  This calculator is NOT directly connected to Namu Securities. Use the results as a reference and **place orders manually**.

- 신용불가 종목 비중이 클 경우 2배 레버리지 달성이 불가능할 수 있으며, 이 때 계산기가 자동으로 최대 가능 레버리지로 조정합니다.  
  If the weight of credit-unavailable stocks is too large, 2x leverage may not be achievable. The calculator will automatically adjust to the maximum possible leverage.

---

## 📦 의존성 / Dependencies

| 패키지 | 용도 / Purpose |
|---|---|
| `yfinance` | 실시간 주가 조회 / Real-time stock price fetching |

---

## 📄 라이선스 / License

MIT License
