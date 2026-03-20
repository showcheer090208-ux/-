# 文件名: main.py
import config
from item_system import generate_items
from npc_boss import NPCBoss
from ai_controller import LLMAgent
from auction_engine import AuctionEngine
from config import Colors

# 🚨 请填入你的 API 配置 🚨
PLAYERS_CONFIG = [
    {"name": "Agent_A", "api_key": "sk-your-key-1", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "color": Colors.AI_1},
    {"name": "Agent_B", "api_key": "sk-your-key-2", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "color": Colors.AI_2},
    {"name": "Agent_C", "api_key": "sk-your-key-3", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "color": Colors.AI_3},
    {"name": "Agent_D", "api_key": "sk-your-key-4", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "color": Colors.AI_4}
]

BOSS_CONFIG = {
    "api_key": "sk-your-key-boss",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini"
}

def main():
    print("🌟 纳什拍卖行 V3.3 (极限高压版) 启动 🌟\n")
    items = generate_items(config.TOTAL_ROUNDS)
    boss = NPCBoss(BOSS_CONFIG["api_key"], BOSS_CONFIG["base_url"], BOSS_CONFIG["model"])
    boss.generate_auction_catalog(items)
    
    agents = []
    for cfg in PLAYERS_CONFIG:
        agents.append(LLMAgent(cfg["name"], cfg["api_key"], cfg["base_url"], cfg["model"], cfg["color"]))
    
    engine = AuctionEngine(agents)
    for round_num in range(1, config.TOTAL_ROUNDS + 1):
        engine.play_round(round_num, items[round_num - 1])
    engine.final_settlement()

if __name__ == "__main__":
    main()