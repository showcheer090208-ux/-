# 文件名: item_system.py
import random
import config

class Item:
    def __init__(self, item_id, item_type, v_anchor, v_actual, inherent_bias):
        self.id = item_id
        self.type = item_type          
        self.v_anchor = v_anchor       
        self.v_actual = v_actual       
        self.inherent_bias = inherent_bias 
        self.public_name = f"标的物 {item_id}"
        self.is_blind_box = False # 盲盒标记

    def get_starting_price(self):
        if self.is_blind_box: return 0
        return int(self.v_anchor * random.uniform(0.4, 0.6))

def generate_items(n=15):
    items = []
    types = ['Normal']*10 + ['Forgery']*3 + ['HiddenGem']*2
    random.shuffle(types)
    for i, t in enumerate(types):
        inherent_bias = random.uniform(-0.1, 0.1)
        if t == 'Normal':
            v_anchor = random.randint(1500, 6000)
            v_actual = int(v_anchor * random.uniform(0.9, 1.1))
        elif t == 'Forgery':
            v_anchor = random.randint(6000, 10000)
            v_actual = random.randint(50, 400)
        elif t == 'HiddenGem':
            v_anchor = random.randint(1000, 2000)
            v_actual = random.randint(7000, 12000)
        items.append(Item(f"Item_{i+1:02d}", t, v_anchor, v_actual, inherent_bias))
    
    # 随机挑选两局作为盲盒局
    blind_indices = random.sample(range(n), 2)
    for idx in blind_indices:
        items[idx].is_blind_box = True
        
    return items

def calculate_appraisal(item, appraisal_level, start_price):
    if item.is_blind_box or appraisal_level == 0:
        return 0, (0, 0) # 盲盒或0级强制为0
        
    # V3.3 动态鉴定费
    cost_rate = 0.10 if appraisal_level == 1 else 0.30
    cost = int(start_price * cost_rate)
    
    width_ratio = 0.40 if appraisal_level == 1 else 0.10
    noise_min, noise_max = (-0.15, 0.15) if appraisal_level == 1 else (-0.03, 0.03)
    random_noise = random.uniform(noise_min, noise_max)
    
    if appraisal_level == 2:
        center = item.v_actual * (1 + random_noise)
        base_val = item.v_actual
    else:
        center = item.v_anchor * (1 + item.inherent_bias + random_noise)
        base_val = item.v_anchor
    
    l_bound = max(0, int(center - (base_val * width_ratio / 2)))
    r_bound = int(center + (base_val * width_ratio / 2))
    return cost, (l_bound, r_bound)