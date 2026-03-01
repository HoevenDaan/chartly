"""Signal backtester — runs the algorithm against historical data to measure performance."""

import math
from datetime import datetime

import numpy as np

from app.analysis.indicators import calculate_indicators
from app.analysis.scoring import calculate_confidence
from app.analysis.signals import generate_signals
from app.utils.logger import get_logger

logger = get_logger("backtester")

MIN_BARS = 250


def run_backtest(symbol: str, history: list[dict], initial_capital: float = 10000.0) -> dict:
    """Run the signal algorithm against historical data and return performance metrics.

    Uses a rolling window: for each day i, indicators are calculated using only
    history[0:i+1] (no look-ahead bias). Trades enter/exit on next-day open.

    Args:
        symbol: Stock ticker symbol.
        history: List of OHLCV dicts with keys: date, open, high, low, close, volume.
        initial_capital: Starting equity in dollars.

    Returns:
        Dict with metrics, trades list, and equity curve.
    """
    if len(history) < MIN_BARS:
        return {
            "symbol": symbol,
            "error": f"Insufficient data: need {MIN_BARS} bars, got {len(history)}",
            "metrics": {},
            "trades": [],
            "equity_curve": [],
        }

    # We need a warmup period for the longest indicator (SMA 200).
    # Start generating signals from bar 200 onward.
    warmup = 200
    equity = initial_capital
    position = None  # None = flat, dict = open position
    trades = []
    equity_curve = []
    daily_returns = []

    first_close = float(history[warmup]["close"])
    buy_hold_shares = initial_capital / first_close

    for i in range(warmup, len(history)):
        bar = history[i]
        current_date = bar["date"]
        current_close = float(bar["close"])
        current_open = float(bar["open"])

        # Buy-and-hold equity for this day
        bh_equity = buy_hold_shares * current_close

        # --- Check exits first (using today's open as exit price) ---
        if position is not None:
            exit_price = None
            exit_reason = None
            days_held = i - position["entry_bar"]

            # Stop loss: check if today's low breached the stop level
            if float(bar["low"]) <= position["stop_loss"]:
                exit_price = max(position["stop_loss"], float(bar["low"]))
                exit_reason = "stop_loss"

            # Time exit: held for 20+ trading days
            elif days_held >= 20:
                exit_price = current_open
                exit_reason = "time_exit"

            else:
                # Generate signal using data up to previous close to decide on today's open
                window = history[: i]
                if len(window) >= 30:
                    indicators = calculate_indicators(window)
                    sig = generate_signals(indicators)
                    conf = calculate_confidence(
                        sig["signal"], indicators, sig["buy_signals"], sig["sell_signals"]
                    )

                    if sig["signal"] == "SELL" and conf >= 50:
                        exit_price = current_open
                        exit_reason = "sell_signal"
                    elif sig["signal"] == "HOLD" and days_held >= 5:
                        exit_price = current_open
                        exit_reason = "hold_exit"

            if exit_price is not None:
                shares = position["shares"]
                trade_return = (exit_price - position["entry_price"]) / position["entry_price"]
                trade_dollars = shares * (exit_price - position["entry_price"])
                equity += trade_dollars

                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": current_date,
                    "entry_price": round(position["entry_price"], 2),
                    "exit_price": round(exit_price, 2),
                    "return_pct": round(trade_return * 100, 2),
                    "return_dollars": round(trade_dollars, 2),
                    "exit_reason": exit_reason,
                    "holding_days": days_held,
                })
                position = None

        # --- Check entries (using today's open as entry price) ---
        if position is None and i < len(history) - 1:
            window = history[: i]
            if len(window) >= 30:
                indicators = calculate_indicators(window)
                sig = generate_signals(indicators)
                conf = calculate_confidence(
                    sig["signal"], indicators, sig["buy_signals"], sig["sell_signals"]
                )

                if sig["signal"] == "BUY" and conf >= 65:
                    entry_price = current_open
                    atr = indicators.get("atr")
                    if atr and entry_price > 0:
                        stop_loss = entry_price - (2 * atr)
                    else:
                        stop_loss = entry_price * 0.95  # fallback 5% stop

                    shares = equity / entry_price
                    position = {
                        "entry_price": entry_price,
                        "entry_date": current_date,
                        "entry_bar": i,
                        "shares": shares,
                        "stop_loss": stop_loss,
                    }

        # Track daily equity
        if position is not None:
            unrealized = position["shares"] * (current_close - position["entry_price"])
            day_equity = equity + unrealized
        else:
            day_equity = equity

        # Daily return for Sharpe calculation
        if equity_curve:
            prev_equity = equity_curve[-1]["equity"]
            if prev_equity > 0:
                daily_returns.append((day_equity - prev_equity) / prev_equity)

        equity_curve.append({
            "date": current_date,
            "equity": round(day_equity, 2),
            "buy_hold_equity": round(bh_equity, 2),
        })

    # Close any remaining position at last close
    if position is not None:
        last_close = float(history[-1]["close"])
        shares = position["shares"]
        trade_return = (last_close - position["entry_price"]) / position["entry_price"]
        trade_dollars = shares * (last_close - position["entry_price"])
        equity += trade_dollars

        trades.append({
            "entry_date": position["entry_date"],
            "exit_date": history[-1]["date"],
            "entry_price": round(position["entry_price"], 2),
            "exit_price": round(last_close, 2),
            "return_pct": round(trade_return * 100, 2),
            "return_dollars": round(trade_dollars, 2),
            "exit_reason": "end_of_data",
            "holding_days": len(history) - 1 - position["entry_bar"],
        })
        position = None

    # --- Calculate metrics ---
    final_equity = equity
    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100
    last_close = float(history[-1]["close"])
    buy_hold_return_pct = ((last_close - first_close) / first_close) * 100

    total_trades = len(trades)
    winning = [t for t in trades if t["return_pct"] > 0]
    losing = [t for t in trades if t["return_pct"] <= 0]
    win_rate = (len(winning) / total_trades * 100) if total_trades > 0 else 0
    avg_win = (sum(t["return_pct"] for t in winning) / len(winning)) if winning else 0
    avg_loss = (sum(t["return_pct"] for t in losing) / len(losing)) if losing else 0

    sum_wins = sum(t["return_dollars"] for t in winning)
    sum_losses = abs(sum(t["return_dollars"] for t in losing))
    profit_factor = (sum_wins / sum_losses) if sum_losses > 0 else (float("inf") if sum_wins > 0 else 0)

    # Max drawdown from equity curve
    max_drawdown = 0
    peak = 0
    for point in equity_curve:
        if point["equity"] > peak:
            peak = point["equity"]
        dd = ((peak - point["equity"]) / peak) * 100 if peak > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    # Sharpe ratio
    if daily_returns and len(daily_returns) > 1:
        mean_ret = np.mean(daily_returns)
        std_ret = np.std(daily_returns, ddof=1)
        sharpe = (mean_ret / std_ret) * math.sqrt(252) if std_ret > 0 else 0
    else:
        sharpe = 0

    metrics = {
        "total_return_pct": round(total_return_pct, 2),
        "buy_hold_return_pct": round(buy_hold_return_pct, 2),
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 1),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.99,
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "final_equity": round(final_equity, 2),
        "initial_capital": initial_capital,
    }

    result = {
        "symbol": symbol,
        "period": {
            "start": history[warmup]["date"],
            "end": history[-1]["date"],
            "trading_days": len(history) - warmup,
        },
        "metrics": metrics,
        "trades": trades,
        "equity_curve": equity_curve,
        "cached_at": datetime.now().isoformat(),
    }

    logger.info(
        f"Backtest {symbol}: {total_return_pct:+.1f}% ({total_trades} trades, "
        f"{win_rate:.0f}% win rate) vs B&H {buy_hold_return_pct:+.1f}%"
    )

    return result
