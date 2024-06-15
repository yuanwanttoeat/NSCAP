import random

def init_hosts(setting):
    hosts = [
        {
            "id": i,
            "status": 0,         # 0: standby, 1: send, 2: resend
            "action_to_do": 0,   # 0: standby, 1: send, 2: resend, 3: stop sending
            "packet_num": 0,   
            "remain_length": setting.total_time,  # remain time to sending
            "wait_time": 0,      # time wait to send
            "collision": False,
            "success_num": 0,
            "collision_num": 0,
            "history": "",       # record history of host's actions
        }
        for i in range(setting.host_num)
    ]
    return hosts

def perform_action(setting, hosts, history):
    ### Perform the action decided in the previous step
    for h in hosts:
        if h["action_to_do"] == 3:  # stop sending
            h["collision"] = False
            h["remain_length"] = 0
            h["collision_num"] += 1
            h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
            history[h["id"]] = "|"
            h["status"] = 0
        else:
            h["status"] = h["action_to_do"]

def check_collisions_and_idle_time(hosts, total_idle_time, history):
    ### Check for collisions and idle time
    sending_list = []
    is_idle_time = True
    for h in hosts:
        if h["status"] == 1:
            sending_list.append(h)
            is_idle_time = False
        if history[h["id"]] != ".":
            is_idle_time = False
            
    if len(sending_list) > 1:
        for h in sending_list:
            h["collision"] = True
    if is_idle_time:
        total_idle_time += 1
    
    return total_idle_time

def print_history(setting, hosts, show_history=False):
    ### Print the history of each host
    if show_history:
        packets_times = setting.gen_packets()
        for h in hosts:
            s = ""
            for t in range(setting.total_time):
                if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                    s += "V"
                    packets_times[h["id"]].pop(0)
                else:
                    s += " "
            print(f"    {s}")
            print(f"h{h['id']}: {h['history']}")

def calculate_metrics(setting, hosts, total_idle_time):
    ### Calculate the success rate, idle rate, and collision rate      
    total_success_num = 0
    for h in hosts:
        total_success_num += h["success_num"]
    total_success_time = total_success_num * setting.packet_time
    total_collision_time = setting.total_time - total_success_time - total_idle_time
    return (
        total_success_time / setting.total_time,
        total_idle_time / setting.total_time,
        total_collision_time / setting.total_time,
    )


def aloha(setting, show_history=False):
    
    hosts = init_hosts(setting)
    packets_times = setting.gen_packets() # Generate packets for each host

    total_idle_time = 0
    for t in range(setting.total_time):
        history = ["." for i in range(setting.host_num)]
        
        ### Generate packets for each host
        for h in hosts:
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                packets_times[h["id"]].pop(0)
                h["packet_num"] += 1

        ### Decide whether each host should send a packet
        for h in hosts:
            h["action_to_do"] = h["status"]
            
            if h["status"] == 0:
                if h["wait_time"] > 0:
                    h["wait_time"] -= 1

                elif h["packet_num"] > 0:
                        # TODO:  change "xxx" to the correct protocol name
                    h["action_to_do"] = 1
                    h["remain_length"] = setting.packet_time
            
        
        ### Perform the action decided in the previous step
        perform_action(setting, hosts, history)

        ### Check for collisions and idle time
        total_idle_time = check_collisions_and_idle_time(hosts, total_idle_time, history)

        ###  Update the host's status and history
        for h in hosts:
            if h["status"] == 1:
                if len(h["history"]) == 0 or (h["history"][-1] != "<" and h["history"][-1] != "-"):
                    history[h["id"]] = "<"
                else:
                    history[h["id"]] = "-"
                h["remain_length"] -= 1
                if h["remain_length"] <= 0:
                    if h["collision"]:
                        h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
                        h["status"] = 0 # standby
                        h["collision_num"] += 1
                        history[h["id"]] = "|"
                    else:
                        h["status"] = 0
                        h["success_num"] += 1
                        h["packet_num"] -= 1
                        history[h["id"]] = ">"
                    h["collision"] = False
            h["history"] += history[h["id"]]
    
    
    print_history(setting, hosts, show_history)
    return calculate_metrics(setting, hosts, total_idle_time)
    
    

def slotted_aloha(setting, show_history=False):
    hosts = init_hosts(setting)
    packets_times = setting.gen_packets() # Generate packets for each host

    total_idle_time = 0
    for t in range(setting.total_time):
        history = ["." for i in range(setting.host_num)]
        
        ### Generate packets for each host
        for h in hosts:
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                packets_times[h["id"]].pop(0)
                h["packet_num"] += 1

        ### Decide whether each host should send a packet
        for h in hosts:
            h["action_to_do"] = h["status"]
            
            if h["status"] == 0:
                if h["wait_time"] > 0:
                    h["wait_time"] -= 1

                elif h["packet_num"] > 0:    
                    if t % setting.packet_time == 0:  # TODO:  change "xxx" to the correct protocol name
                        h["action_to_do"] = 1       
                        h["remain_length"] = setting.packet_time
                    
            
            elif h["status"] == 2 and t % setting.packet_time == 0: # TODO:  change "xxx" to the correct protocol name
                r = random.random()
                if r < setting.p_resend:
                    h["action_to_do"] = 1
                    h["remain_length"] = setting.packet_time
        
        ### Perform the action decided in the previous step
        perform_action(setting, hosts, history)

        ### Check for collisions and idle time
        total_idle_time = check_collisions_and_idle_time(hosts, total_idle_time, history)

        ###  Update the host's status and history
        for h in hosts:
            if h["status"] == 1:
                if len(h["history"]) == 0 or (h["history"][-1] != "<" and h["history"][-1] != "-"):
                    history[h["id"]] = "<"
                else:
                    history[h["id"]] = "-"
                h["remain_length"] -= 1
                if h["remain_length"] <= 0:
                    if h["collision"]:
                        h["status"] = 2 # resend 
                        h["collision_num"] += 1
                        history[h["id"]] = "|"
                    else:
                        h["status"] = 0
                        h["success_num"] += 1
                        h["packet_num"] -= 1
                        history[h["id"]] = ">"
                    h["collision"] = False
            h["history"] += history[h["id"]]
    
    
    print_history(setting, hosts, show_history)
    return calculate_metrics(setting, hosts, total_idle_time)
    
def csma(setting, one_persistent=False, show_history=False):
    hosts = init_hosts(setting)
    packets_times = setting.gen_packets() # Generate packets for each host

    total_idle_time = 0
    for t in range(setting.total_time):
        history = ["." for i in range(setting.host_num)]
        
        ### Generate packets for each host
        for h in hosts:
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                packets_times[h["id"]].pop(0)
                h["packet_num"] += 1

        ### Decide whether each host should send a packet
        for h in hosts:
            h["action_to_do"] = h["status"]
            
            if h["status"] == 0:
                if h["wait_time"] > 0:
                    h["wait_time"] -= 1

                elif h["packet_num"] > 0:
                    others_sending = False
                    for others in hosts:
                        if others["id"] == h["id"]:
                            continue
                        if (
                            setting.link_delay >= 0
                            and t > (setting.link_delay + 1)
                            and (
                                others["history"][t - (setting.link_delay + 1)] == "-"
                                or others["history"][t - (setting.link_delay + 1)] == "<"
                            )
                        ):
                            others_sending = True
                    
                    if not others_sending:
                        h["action_to_do"] = 1
                        h["remain_length"] = setting.packet_time
                    else:
                        if not one_persistent:
                            h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
        
        ### Perform the action decided in the previous step
        perform_action(setting, hosts, history)

        ### Check for collisions and idle time
        total_idle_time = check_collisions_and_idle_time(hosts, total_idle_time, history)

        ###  Update the host's status and history
        for h in hosts:
            if h["status"] == 1:
                if len(h["history"]) == 0 or (h["history"][-1] != "<" and h["history"][-1] != "-"):
                    history[h["id"]] = "<"
                else:
                    history[h["id"]] = "-"
                h["remain_length"] -= 1
                if h["remain_length"] <= 0:
                    if h["collision"]:
                        h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
                        h["status"] = 0 # standby
                        h["collision_num"] += 1
                        history[h["id"]] = "|"
                    else:
                        h["status"] = 0
                        h["success_num"] += 1
                        h["packet_num"] -= 1
                        history[h["id"]] = ">"
                    h["collision"] = False
            h["history"] += history[h["id"]]

    print_history(setting, hosts, show_history)
    return calculate_metrics(setting, hosts, total_idle_time)

def csma_cd(setting, one_persistent=False, show_history=False):
    hosts = init_hosts(setting)
    packets_times = setting.gen_packets() # Generate packets for each host

    total_idle_time = 0
    for t in range(setting.total_time):
        history = ["." for i in range(setting.host_num)]
        
        ### Generate packets for each host
        for h in hosts:
            if len(packets_times[h["id"]]) > 0 and packets_times[h["id"]][0] == t:
                packets_times[h["id"]].pop(0)
                h["packet_num"] += 1

        ### Decide whether each host should send a packet
        for h in hosts:
            h["action_to_do"] = h["status"]
            
            if h["status"] == 0:
                if h["wait_time"] > 0:
                    h["wait_time"] -= 1

                elif h["packet_num"] > 0:
                    others_sending = False
                    for others in hosts:
                        if others["id"] == h["id"]:
                            continue
                        if (
                            setting.link_delay >= 0
                            and t > (setting.link_delay + 1)
                            and (
                                others["history"][t - (setting.link_delay + 1)] == "-"
                                or others["history"][t - (setting.link_delay + 1)] == "<"
                            )
                        ):
                            others_sending = True
                    
                    if not others_sending:
                        h["action_to_do"] = 1
                        h["remain_length"] = setting.packet_time
                    else:
                        if not one_persistent:
                            h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
            
            elif h["status"] == 1 :    # TODO:  change "xxx" to the correct protocol name
                others_sending = False
                for others in hosts:
                    if others["id"] == h["id"]:
                        continue
                    if (
                        setting.link_delay >= 0
                        and t > (setting.link_delay + 1)
                        and (
                            others["history"][t - (setting.link_delay + 1)] == "-"
                            or others["history"][t - (setting.link_delay + 1)] == "<"
                        )
                    ):
                        others_sending = True
                if others_sending:
                    h["action_to_do"] = 3
            
        
        ### Perform the action decided in the previous step
        perform_action(setting, hosts, history)

        ### Check for collisions and idle time
        total_idle_time = check_collisions_and_idle_time(hosts, total_idle_time, history)

        ###  Update the host's status and history
        for h in hosts:
            if h["status"] == 1:
                if len(h["history"]) == 0 or (h["history"][-1] != "<" and h["history"][-1] != "-"):
                    history[h["id"]] = "<"
                else:
                    history[h["id"]] = "-"
                h["remain_length"] -= 1
                if h["remain_length"] <= 0:
                    if h["collision"]:
                        h["wait_time"] = random.randint(0, setting.max_collision_wait_time)
                        h["status"] = 0 # standby
                        h["collision_num"] += 1
                        history[h["id"]] = "|"
                    else:
                        h["status"] = 0
                        h["success_num"] += 1
                        h["packet_num"] -= 1
                        history[h["id"]] = ">"
                    h["collision"] = False
            h["history"] += history[h["id"]]
    
    print_history(setting, hosts, show_history)
    return calculate_metrics(setting, hosts, total_idle_time)
