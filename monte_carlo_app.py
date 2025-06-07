import streamlit as st
import numpy as np
import tempfile
import base64
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.animation import PillowWriter
from streamlit.components.v1 import html

st.set_page_config(layout="wide")
st.title("🎲 Симуляция сделок Монте-Карло")

# === Ввод параметров ===
with st.sidebar:
    st.header("⚙️ Параметры симуляции")
    init_balance = st.number_input("💰 Начальный баланс", value=100.0, help="Стартовая сумма в каждой симуляции")
    winrate = st.slider("🎯 Winrate (%)", 0, 100, 50, help="Процент выигрыша по стратегии")
    rr = st.number_input("⚖️ Reward/Risk (RR)", value=2.0, help="Соотношение прибыли к риску в одной сделке")
    risk_pct = st.number_input("🔥 Риск на сделку (%)", value=2.0, help="Сколько % капитала рискуется в каждой сделке")
    num_trades = st.number_input("🔁 Сделок в симуляции", min_value=1, max_value=1000, value=50, help="Количество сделок на одну симуляцию")
    num_simulations = st.number_input("📊 Кол-во симуляций", min_value=1, max_value=10000, value=100, help="Количество параллельных симуляций")
    liquidation_pct = st.number_input("💀 Порог ликвидации (%)", min_value=0.0, max_value=100.0, value=1.0,
                                      help="Ликвидация при падении ниже X% от начального баланса")

# === Симуляция ===
def simulate():
    all_data = []
    final_balances = []
    liquidation_hits = 0
    liquidation_on_trade = []
    max_drawdowns = []

    threshold = init_balance * (liquidation_pct / 100)

    for _ in range(int(num_simulations)):
        balance = init_balance
        peak = balance
        row = [balance]
        liq_hit = None
        max_dd = 0

        for t in range(int(num_trades)):
            if balance <= threshold:
                balance = 0
                if liq_hit is None:
                    liquidation_hits += 1
                    liq_hit = t + 1
                    liquidation_on_trade.append(liq_hit)
                row.append(0)
                continue

            is_win = np.random.rand() < winrate / 100
            risk = balance * risk_pct / 100
            pnl = risk * rr if is_win else -risk
            balance += pnl
            peak = max(peak, balance)
            dd = (peak - balance) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            row.append(max(balance, 0))

        all_data.append(row)
        final_balances.append(balance)
        max_drawdowns.append(max_dd)

    return (np.array(all_data),
            np.array(final_balances),
            liquidation_hits,
            liquidation_on_trade,
            np.array(max_drawdowns))

# === Запуск
if st.button("▶️ Запустить симуляцию"):
    data, balances, liq_count, liq_trades, drawdowns = simulate()
    x = np.arange(int(num_trades) + 1)

    # === Метрики
    st.subheader("📊 Общая статистика")
    col1, col2, col3 = st.columns(3)
    col1.metric("📌 Медиана", f"{np.median(balances):,.2f}")
    col1.metric("🧠 Среднее", f"{np.mean(balances):,.2f}")
    col2.metric("🔻 Минимум", f"{np.min(balances):,.2f}")
    col2.metric("🟢 Максимум", f"{np.max(balances):,.2f}")
    col3.metric("🎲 Стд. отклонение", f"{np.std(balances):,.2f}")
    col3.metric("📊 Симуляций", str(len(balances)))
    st.metric("💀 Ликвидации", f"{liq_count} из {len(balances)} ({liq_count / len(balances) * 100:.1f}%)")

    # Доп. вывод:
    st.subheader("📈 Дополнительные показатели")
    st.write(f"🧪 Медианная просадка: **{np.median(drawdowns) * 100:.2f}%**")
    st.write(f"📉 Средняя просадка: **{np.mean(drawdowns) * 100:.2f}%**")
    st.write(f"💵 Симуляций с итогом > начального капитала: **{np.sum(balances > init_balance)} ({np.mean(balances > init_balance) * 100:.1f}%)**")
    st.write(f"💰 Симуляций с итогом > 2× капитала: **{np.sum(balances > init_balance * 2)} ({np.mean(balances > init_balance * 2) * 100:.1f}%)**")
    st.write(f"🚀 Симуляций с итогом > 10× капитала: **{np.sum(balances > init_balance * 10)} ({np.mean(balances > init_balance * 10) * 100:.1f}%)**")

    # Статус стратегии
    if np.median(balances) > init_balance:
        st.success("✅ Стратегия прибыльная")
    else:
        st.error("❌ Стратегия убыточная")

    # Порог безубыточности
    breakeven_wr = 100 / (1 + rr)
    st.info(f"⚠️ Порог безубыточности: **{breakeven_wr:.2f}%** при RR = {rr:.2f}")

    # 📈 Симуляции
    st.subheader("📉 Графики")
    st.caption("⚠️ Отображается максимум 100 симуляций (для читаемости)")

    # Все симуляции
    st.markdown("#### 📈 100 симуляций капитала")
    fig1, ax1 = plt.subplots()
    for i in range(min(100, len(data))):
        ax1.plot(x, data[i])
    st.pyplot(fig1)

    # Лучшие/худшие
    st.markdown("#### 🟢 10 лучших | 🔻 10 худших")
    fig2, ax2 = plt.subplots()
    for idx in balances.argsort()[-10:]:
        ax2.plot(x, data[idx], linestyle='--', alpha=0.7)
    for idx in balances.argsort()[:10]:
        ax2.plot(x, data[idx], linestyle='-', alpha=0.7)
    st.pyplot(fig2)

    # Гистограмма итогов
    st.markdown("#### 📊 Распределение финальных балансов")
    fig3, ax3 = plt.subplots()
    ax3.hist(balances, bins=50, color="skyblue", edgecolor="black")
    ax3.axvline(init_balance, color="red", linestyle="--", label="Старт")
    ax3.legend()
    st.pyplot(fig3)

    # === 🧠 Карта вероятностей
    st.subheader("🧠 Карта вероятностей (процент ниже стартового баланса)")
    st.caption("На каком шаге, сколько симуляций оказались ниже стартового баланса.")
    heat = [np.sum(data[:, j] < init_balance) / len(data) for j in range(1, int(num_trades) + 1)]
    fig5, ax5 = plt.subplots()
    ax5.plot(range(1, int(num_trades) + 1), heat)
    ax5.set_ylim(0, 1)
    st.pyplot(fig5)

    # Распределение ликвидаций
    if liq_trades:
        st.markdown("#### 💀 Распределение ликвидаций по сделкам")
        fig4, ax4 = plt.subplots()
        ax4.hist(liq_trades, bins=int(num_trades), edgecolor="black")
        st.pyplot(fig4)

    # === 🌡️ Профиль риска/доходности
    with st.expander("🌡️ Профиль риска/доходности (Heatmap)"):
        st.markdown("Показывает медианный итог при разных сочетаниях Winrate и Риска.")
        wrates = np.arange(30, 81, 5)
        risks = np.arange(0.5, 5.5, 0.5)
        heatmap = np.zeros((len(risks), len(wrates)))
        for i, r in enumerate(risks):
            for j, w in enumerate(wrates):
                sims = []
                for _ in range(100):
                    bal = init_balance
                    for _ in range(50):
                        is_win = np.random.rand() < w / 100
                        risk_amt = bal * r / 100
                        pnl = risk_amt * rr if is_win else -risk_amt
                        bal += pnl
                        if bal <= 0:
                            bal = 0
                            break
                    sims.append(bal)
                heatmap[i, j] = np.median(sims)
        fig7, ax7 = plt.subplots()
        im = ax7.imshow(heatmap, cmap="YlGnBu", origin="lower", aspect="auto")
        ax7.set_xticks(np.arange(len(wrates)))
        ax7.set_xticklabels([f"{w}%" for w in wrates])
        ax7.set_yticks(np.arange(len(risks)))
        ax7.set_yticklabels([f"{r:.1f}%" for r in risks])
        ax7.set_xlabel("🎯 Winrate (%)")
        ax7.set_ylabel("🔥 Риск на сделку (%)")
        ax7.set_title("📊 Медианный итоговый баланс")
        fig7.colorbar(im, ax=ax7, label="💰 Баланс")
        st.pyplot(fig7)

    # 🎞️ Анимация симуляций
    st.markdown("#### 🎞️ Анимированная визуализация (до 10 симуляций)")
    st.caption("Показывает, как развиваются балансы по ходу сделок.")

    num_animated = min(10, len(data))
    fig_anim, ax_anim = plt.subplots()
    ax_anim.set_xlim(0, num_trades)
    ax_anim.set_ylim(0, np.max(data[:num_animated]) * 1.1)
    lines_anim = [ax_anim.plot([], [], lw=1)[0] for _ in range(num_animated)]


    def init_anim():
        for line in lines_anim:
            line.set_data([], [])
        return lines_anim


    def update_anim(frame):
        for i, line in enumerate(lines_anim):
            line.set_data(np.arange(frame), data[i, :frame])
        return lines_anim


    ani = animation.FuncAnimation(fig_anim, update_anim, frames=num_trades + 1, init_func=init_anim, blit=True,
                                  interval=100)

    # Сохраняем как GIF и вставляем как анимацию
    with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as f:
        ani.save(f.name, writer=PillowWriter(fps=10))
        gif_bytes = open(f.name, "rb").read()
        gif_base64 = base64.b64encode(gif_bytes).decode()
        gif_html = f"""
        <img src="data:image/gif;base64,{gif_base64}" width="100%" height="400" alt="Анимация симуляций">
        """
        html(gif_html, height=420)