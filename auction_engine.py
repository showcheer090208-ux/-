# 文件名: auction_engine.py
import random
import time
import config
from config import Colors, calculate_interest

class PlayerState:
    def __init__(self, name):
        self.name = name
        self.cash = config.INITIAL_CASH
        self.debt = 0
        self.inventory = []
        self.is_bankrupt = False
        self.has_pass = True # 全局单次 PASS 特权
        
        self.stats_bids_this_round = 0
        self.stats_appraisal_spent = 0

    def max_purchasing_power(self):
        return self.cash + (config.MAX_DEBT - self.debt) if not self.is_bankrupt else 0

    def deduct_funds(self, amount):
        if amount <= self.cash:
            self.cash -= amount
        else:
            shortfall = amount - self.cash
            self.cash = 0
            self.debt += shortfall
            if self.debt >= config.MAX_DEBT: self.is_bankrupt = True

class PlayerWrapper:
    def __init__(self, agent):
        self.agent = agent
        self.state = PlayerState(agent.name)

class AuctionEngine:
    def __init__(self, agents_list):
        self.players = [PlayerWrapper(agent) for agent in agents_list]

    def _run_reflection_phase(self, round_num, item, winner_name, winning_bid, hidden_cost, net_profit, history_log):
        print(f"\n{Colors.BLUE}🧠 赛后复盘阶段：AI 正在消化本轮信息并更新私人档案...{Colors.RESET}")
        round_data = {
            "round_num": round_num, "item_name": item.public_name, "v_actual": item.v_actual,
            "winner_name": winner_name, "winning_bid": winning_bid, "hidden_cost": hidden_cost,
            "net_profit": net_profit, "history": "\n".join(history_log)
        }
        for p in self.players:
            if not p.state.is_bankrupt:
                opponent_names = [opp.state.name for opp in self.players if opp != p]
                new_memories = p.agent.reflect_and_memorize(round_data, opponent_names)
                print(f"\n{p.agent.color}📖 [{p.state.name} 的绝密档案更新]{Colors.RESET}")
                if isinstance(new_memories, dict) and new_memories:
                    for target, evaluation in new_memories.items():
                        print(f"  ↳ 对 {target} 的评价: {evaluation}")
                time.sleep(1)
        print("\n" + "="*60)

    def play_round(self, round_num, item):
        blind_title = f"{Colors.RED}[!!! 盲盒夜 !!!]{Colors.RESET} " if item.is_blind_box else ""
        print(f"\n{'='*60}\n📢 第 {round_num}/{config.TOTAL_ROUNDS} 轮拍卖开始! {blind_title}\n{'='*60}")
        start_price = item.get_starting_price()
        
        print(f"\n{Colors.CYAN}╔════════════ [上帝视角 - 物品真相] ════════════╗{Colors.RESET}")
        print(f"║ 物品花名: {Colors.MAGENTA}{item.public_name}{Colors.RESET}")
        print(f"║ 真实价值: {Colors.GREEN if item.type=='HiddenGem' else Colors.RED}${item.v_actual}{Colors.RESET} (类型: {item.type})")
        print(f"║ 基础起拍: ${start_price}")
        if item.is_blind_box: print(f"║ {Colors.RED}状态: 盲盒局，起拍锁定为 0，全员鉴定功能被屏蔽！{Colors.RESET}")
        print(f"{Colors.CYAN}╚═══════════════════════════════════════════════╝{Colors.RESET}\n")
        
        status_map = {p.state.name: "OUT" if p.state.is_bankrupt else "ON" for p in self.players}
        history_log = [f"【起拍价】: ${start_price}"]

        # 1. 独立排队鉴定
        for p in self.players:
            if status_map[p.state.name] == "ON":
                level = p.agent.choose_appraisal(p.state, start_price, item.public_name, round_num, config.TOTAL_ROUNDS, item.is_blind_box)
                cost, bounds = p.agent.receive_appraisal(item, level, start_price)
                p.state.deduct_funds(cost)
                p.state.stats_appraisal_spent = cost
                if not item.is_blind_box: history_log.append(f"{p.state.name} 花费 ${cost} 进行了鉴定。")
                if p.state.is_bankrupt: status_map[p.state.name] = "OUT"
                time.sleep(1) 

        active_bidders = [p for p in self.players if status_map[p.state.name] == "ON"]
        if not active_bidders: return

        start_index = random.randint(0, len(active_bidders) - 1)
        active_bidders = active_bidders[start_index:] + active_bidders[:start_index]
        current_bid = 0
        current_winner = None
        
        # 2. 环形叫价
        while len(active_bidders) > 1 or (len(active_bidders) == 1 and current_winner is None):
            current_player = active_bidders[0]
            min_bid = max(start_price, current_bid + max(config.MIN_BID_ABS, int(current_bid * config.MIN_BID_RATE))) if current_bid > 0 else start_price
            
            opp_info = [{"name": p.state.name, "status": status_map[p.state.name], "cash": p.state.cash, "loan_avail": config.MAX_DEBT - p.state.debt} for p in self.players if p != current_player]
            
            print(f"⏳ 等待 [{current_player.state.name}] 决策... (门槛: ${min_bid})")
            action = current_player.agent.make_bid(current_player.state, opp_info, current_bid, min_bid, item.public_name, round_num, config.TOTAL_ROUNDS, item.is_blind_box)
            time.sleep(1) 

            if action == "FOLD":
                status_map[current_player.state.name] = "FOLD"
                history_log.append(f"{current_player.state.name} 退出竞价 (FOLD)。")
                print(f"🏃 {current_player.agent.color}{current_player.state.name} 退出本轮竞价。{Colors.RESET}")
                active_bidders.pop(0)
            else:
                try:
                    bid_amount = int(action)
                    if bid_amount > current_player.state.max_purchasing_power():
                        status_map[current_player.state.name] = "FOLD"
                        active_bidders.pop(0)
                    else:
                        current_bid = bid_amount
                        current_winner = current_player
                        history_log.append(f"{current_player.state.name} 出价: ${bid_amount}。")
                        print(f"📣 {current_player.agent.color}{current_player.state.name} 强势出价: ${bid_amount}{Colors.RESET}")
                        active_bidders.append(active_bidders.pop(0))
                except Exception:
                    status_map[current_player.state.name] = "FOLD"
                    active_bidders.pop(0)

        # 3. 终局确认与处刑账单
        final_winner_name, final_bid, hidden_cost, net_profit = "无人", 0, 0, 0
        
        if current_winner and len(active_bidders) == 1:
            winner = active_bidders[0]
            if winner == current_winner:
                if winner.state.has_pass:
                    confirm = winner.agent.confirm_win(winner.state, current_bid, item.public_name, round_num, config.TOTAL_ROUNDS, item.is_blind_box)
                    time.sleep(1) 
                    if confirm:
                        print(f"✅ {winner.agent.color}{winner.state.name} 确认接盘！{Colors.RESET}")
                    else:
                        print(f"🚫 {winner.agent.color}{winner.state.name} 感到恐惧，使用了全局仅一次的【PASS】特权逃脱！{Colors.RESET}")
                        winner.state.has_pass = False
                        history_log.append(f"{winner.state.name} 使用了唯一 PASS 权逃亡，物品流拍。")
                        self._run_reflection_phase(round_num, item, "无人", 0, 0, 0, history_log)
                        return
                else:
                    print(f"🚨 {Colors.RED}【系统强制执行】 {winner.state.name} 的 PASS 特权已在历史轮次耗尽！丧失拒绝权，强制按 ${current_bid} 压哨成交！{Colors.RESET}")
                    history_log.append(f"{winner.state.name} 因 PASS 耗尽被强制接盘。")
                
                # 计算处刑账单
                pre_debt = winner.state.debt
                winner.state.deduct_funds(current_bid)
                post_debt = winner.state.debt
                marginal_interest = calculate_interest(post_debt) - calculate_interest(pre_debt)
                
                hidden_cost = winner.state.stats_appraisal_spent + marginal_interest
                net_profit = item.v_actual - current_bid - hidden_cost
                
                winner.state.inventory.append(item)
                final_winner_name = winner.state.name
                final_bid = current_bid
                history_log.append(f"最终成交。算上鉴定与利息，总隐性成本 ${hidden_cost}，该单净盈亏 ${net_profit}。")
                
                # 打印血淋淋的小票
                print(f"\n{Colors.MAGENTA}🧾 拍卖行结算单 🧾{Colors.RESET}")
                print(f"买家: {winner.state.name} | 举牌价: ${current_bid}")
                print(f"隐性成本: 鉴定费 ${winner.state.stats_appraisal_spent} + 本单高利贷利息 ${marginal_interest}")
                print(f"真实价值: ${item.v_actual}")
                color_net = Colors.GREEN if net_profit >= 0 else Colors.RED
                print(f"绝对净盈亏: {color_net}${net_profit}{Colors.RESET}")
        else:
            print("💨 无人接盘，流拍。")
            history_log.append("流拍。")

        self._run_reflection_phase(round_num, item, final_winner_name, final_bid, hidden_cost, net_profit, history_log)

    def final_settlement(self):
        print(f"\n{Colors.MAGENTA}════════════════════ 最终资产大清算 ════════════════════{Colors.RESET}")
        leaderboard = []
        for p in self.players:
            v_sum = sum(i.v_actual for i in p.state.inventory)
            debt_penalty = calculate_interest(p.state.debt)
            score = p.state.cash + v_sum - p.state.debt - debt_penalty # 结算是要还本金的！
            leaderboard.append({"name": p.state.name, "score": score, "state": p.state, "agent": p.agent})
            
        leaderboard.sort(key=lambda x: x["score"], reverse=True)
        for rank, data in enumerate(leaderboard):
            state = data["state"]
            score = data["score"]
            debt_penalty = calculate_interest(state.debt)
            print(f"\n🏅 排名 {rank+1}: {data['agent'].color}{state.name}{Colors.RESET} | 最终净资产: {Colors.GREEN if score>0 else Colors.RED}{score}{Colors.RESET}")
            print(f"   💵 剩余现金: ${state.cash} | 💳 未还本金: ${state.debt} | 💸 阶梯利息罚金: ${debt_penalty}")
            print(f"   📦 物品数: {len(state.inventory)}")