# 文件名: ai_controller.py
import json
import re
import time
from openai import OpenAI
from item_system import calculate_appraisal
import config
from config import Colors, MAX_DEBT, calculate_interest

class LLMAgent:
    def __init__(self, name, api_key, base_url, model_name, color):
        self.name = name
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.color = color
        
        self.current_appraisal = (0, 0)
        self.sunk_cost_this_round = 0 
        self.personal_memory = {} 
        
        self.system_prompt = """
        你是量化拍卖博弈AI。目标：最大化绝对净盈亏 = (物品真值 - 出价 - 鉴定费 - 产生的阶梯贷款利息)。
        【极度高压警告】：贷款利息按阶梯累进(20%、35%、50%)，不计利息盲目加杠杆是极其愚蠢的！
        【绝对指令】："thought" 必须用纯中文推理计算盈亏！必须按要求回复 JSON。
        """

    def _call_llm_with_retry(self, prompt):
        delays = [2, 4, 8, 12, 16]
        for i, delay in enumerate(delays):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": prompt}],
                    temperature=0.3, response_format={ "type": "json_object" }
                )
                return json.loads(response.choices[0].message.content.strip())
            except Exception as e:
                if i == len(delays) - 1: return {"thought": f"API报错: {e}", "action": "FOLD"}
                time.sleep(delay)

    def receive_appraisal(self, item, level, start_price):
        cost, bounds = calculate_appraisal(item, level, start_price)
        self.current_appraisal = bounds
        self.sunk_cost_this_round = cost
        return cost, bounds

    def choose_appraisal(self, my_state, start_price, item_name, round_num, total_rounds, is_blind_box):
        self.sunk_cost_this_round = 0
        if is_blind_box:
            return 0 # 盲盒自动返回 0 级

        cost_lv1 = int(start_price * 0.10)
        cost_lv2 = int(start_price * 0.30)
        
        prompt = f"""
        【进度】{round_num}/{total_rounds} 轮。
        【资产】现金: ${my_state.cash} | 已用贷款: ${my_state.debt}/${MAX_DEBT} (当前累计利息罚金: ${calculate_interest(my_state.debt)})
        【标的】[{item_name}] 基础起拍价: ${start_price}。
        
        【动态鉴定费】
        - 档位 0：免费。误差极大(±50%)。
        - 档位 1 (起拍价10%)：花费 ${cost_lv1}。中等(±15%)。
        - 档位 2 (起拍价30%)：花费 ${cost_lv2}。大师级，直达真值。
        回复 JSON: {{"thought": "中文推演成本与风险", "action": "LEVEL 0" 或 "LEVEL 1" 或 "LEVEL 2"}}
        """
        result = self._call_llm_with_retry(prompt)
        print(f"{self.color}[{self.name} OS]: {result.get('thought', '')}{Colors.RESET}")
        match = re.search(r'LEVEL\s*([012])', str(result.get('action', '')), re.IGNORECASE)
        return int(match.group(1)) if match else 0

    def make_bid(self, my_state, opp_info, current_bid, min_bid, item_name, round_num, total_rounds, is_blind_box):
        opp_str = "\n".join([f"- {opp['name']} [{opp['status']}]: 现金 ${opp['cash']} | 剩余贷款 ${opp['loan_avail']} | 你对它的定性: {self.personal_memory.get(opp['name'], '暂无')}" for opp in opp_info])
        
        # 计算若以此价成交的财务压力
        total_cost_if_bid = min_bid + self.sunk_cost_this_round
        new_debt_needed = max(0, min_bid - my_state.cash)
        projected_total_debt = my_state.debt + new_debt_needed
        projected_interest = calculate_interest(projected_total_debt)
        marginal_interest = projected_interest - calculate_interest(my_state.debt)
        
        appraisal_info = f"私人估值区间: ${self.current_appraisal[0]} - ${self.current_appraisal[1]}" if not is_blind_box else "【本轮为盲盒轮！禁止鉴定，纯靠猜忌与诈唬！】"
        pass_warning = "" if my_state.has_pass else "【严重警告：你全局唯一的 PASS 权已耗尽！只要出价并在最后胜出，将强制接盘无法反悔！】"

        prompt = f"""
        【进度】{round_num}/{total_rounds} 轮。标的: [{item_name}]
        {appraisal_info}
        {pass_warning}
        
        【极限高压算账】
        当前最高价: ${current_bid}。最低需出: ${min_bid}。本轮已付鉴定费: ${self.sunk_cost_this_round}。
        你当前现金: ${my_state.cash}。若出价 ${min_bid}，需新增贷款: ${new_debt_needed}。
        加上阶梯利息，这笔出价将产生额外的边际利息成本: ${marginal_interest}！
        你的预估总成本为 = {min_bid} (出价) + {self.sunk_cost_this_round} (鉴定) + {marginal_interest} (利息) = ${min_bid + self.sunk_cost_this_round + marginal_interest}！
        
        【对手情报】
        {opp_str}
        
        回复 JSON: {{"thought": "中文算计净盈亏和对手心理", "action": "BID <数字>" 或 "FOLD"}}
        """
        result = self._call_llm_with_retry(prompt)
        print(f"{self.color}[{self.name} OS]: {result.get('thought', '')}{Colors.RESET}")
        match = re.search(r'(BID\s*(\d+)|FOLD)', str(result.get('action', '')), re.IGNORECASE)
        if match: return str(match.group(2)) if "BID" in match.group(1).upper() else "FOLD"
        return "FOLD"

    def confirm_win(self, my_state, current_bid, item_name, round_num, total_rounds, is_blind_box):
        new_debt_needed = max(0, current_bid - my_state.cash)
        marginal_interest = calculate_interest(my_state.debt + new_debt_needed) - calculate_interest(my_state.debt)
        appraisal_info = f"区间: ${self.current_appraisal[0]} - ${self.current_appraisal[1]}" if not is_blind_box else "【盲盒轮无估值】"
        
        prompt = f"""
        【成交确认】[{item_name}] 叫价停留在: ${current_bid}。
        {appraisal_info}
        
        极限成本核算：出价 ${current_bid} + 鉴定费 ${self.sunk_cost_this_round} + 新增利息 ${marginal_interest} = 你的真实成本为 ${current_bid + self.sunk_cost_this_round + marginal_interest}。
        你拥有全局最后 1 次放弃特权。
        回复 JSON: {{"thought": "核算成本，这价接盘值得吗", "action": "CONFIRM" 或 "PASS"}}
        """
        result = self._call_llm_with_retry(prompt)
        print(f"{self.color}[{self.name} OS]: {result.get('thought', '')}{Colors.RESET}")
        match = re.search(r'(CONFIRM|PASS)', str(result.get('action', '')), re.IGNORECASE)
        return match.group(1).upper() == "CONFIRM" if match else False

    def reflect_and_memorize(self, round_data, opponent_names):
        old_memories = "\n".join([f"- {name}: {self.personal_memory.get(name, '暂无')}" for name in opponent_names])
        prompt = f"""
        【赛后复盘与记忆更新】第 {round_data['round_num']} 轮结束。
        标的: {round_data['item_name']} | 真实价值 (V_actual): ${round_data['v_actual']}
        本轮胜者: {round_data['winner_name']} | 最终成交价: ${round_data['winning_bid']}
        胜者隐性成本(鉴定+利息): ${round_data['hidden_cost']} | 绝对净盈亏: ${round_data['net_profit']}
        
        【本轮行为记录】
        {round_data['history']}
        
        【你过去的评价】
        {old_memories}
        
        结合数据更新并【覆写】对每个对手的性格、财力、策略评价。
        回复 JSON: {{"Agent_A": "评价...", "Agent_B": "评价..."}}
        """
        result = self._call_llm_with_retry(prompt)
        for name in opponent_names:
            if name in result: self.personal_memory[name] = result[name]
        return result