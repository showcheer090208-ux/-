# 文件名: config.py
# ==========================================
# 纳什拍卖行 V3.3 (极限高压版) - 全局配置
# ==========================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    # 给 AI 准备的专属个性色
    AI_3 = '\033[94m' # Blue
    AI_1 = '\033[96m' # Cyan
    AI_2 = '\033[93m' # Yellow
    AI_4 = '\033[95m' # Magenta
    RESET = '\033[0m'

INITIAL_CASH = 15000
MAX_DEBT = 30000
TOTAL_ROUNDS = 15

MIN_BID_RATE = 0.08
MIN_BID_ABS = 150

# 阶梯利息计算公式 (全局统一口径)
def calculate_interest(debt):
    if debt <= 0: return 0
    interest = 0
    if debt > 20000:
        interest += (debt - 20000) * 0.50
        interest += 10000 * 0.35
        interest += 10000 * 0.20
    elif debt > 10000:
        interest += (debt - 10000) * 0.35
        interest += 10000 * 0.20
    else:
        interest += debt * 0.20
    return int(interest)