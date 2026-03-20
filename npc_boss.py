# 文件名: npc_boss.py
import json
import re
import time
import random
from openai import OpenAI
from config import Colors

class NPCBoss:
    def __init__(self, api_key, base_url, model_name):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def generate_auction_catalog(self, items):
        print(f"{Colors.MAGENTA}🎭 拍卖行老板正在为 15 件物品命名...{Colors.RESET}")
        item_data = [{"id": i.id, "type": i.type, "v_anchor": i.v_anchor} for i in items]
            
        prompt = f"""
        你是一个拍卖行老板。请为这 15 个物品起一个符合其价格特征的【名字】。
        要求：
        1. Forgery (伪造品/高标价)：起极度浮夸、像国宝一样的名字。
        2. HiddenGem (捡漏品/低标价)：起破烂、不值钱的名字。
        3. Normal (正品)：起正常的古董或艺术品名字。
        只输出 JSON 数组：[ {{"id": "Item_01", "name": "大明宣德炉"}} ]
        数据：{json.dumps(item_data, ensure_ascii=False)}
        """
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name, messages=[{"role": "user", "content": prompt}], temperature=0.7
                )
                content = re.sub(r'^```json\s*|\s*```$', '', response.choices[0].message.content.strip(), flags=re.IGNORECASE)
                catalog = json.loads(content)
                for cat_item in catalog:
                    for item in items:
                        if item.id == cat_item["id"]:
                            item.public_name = cat_item["name"]
                            break
                print(f"{Colors.GREEN}✅ 物品命名完成！{Colors.RESET}")
                return
            except Exception as e:
                time.sleep(2)
                
        print(f"{Colors.RED}⚠️ 老板 API 持续拥堵，启用本地备用词库。{Colors.RESET}")
        fallback_names = ["生锈铁剑", "神秘瓷瓶", "残破字画", "宫廷玉佩", "远古化石", "无名氏手稿", "黄铜怀表", "蒙尘王冠"]
        for item in items:
            item.public_name = f"{random.choice(fallback_names)} (编号{item.id[-2:]})"