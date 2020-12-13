from scipy.stats import poisson
import simpy
import copy
import numpy as np

class Packet(object):
  def __init__(self, packet_id, source, transmit_start_time, received_by_all, visited_routers, path_taken, previous_link, path_cost):
    self.packet_id = packet_id
    self.source = source
    self.transmit_start_time = transmit_start_time
    self.visited_routers = visited_routers if visited_routers else []
    self.path_taken = path_taken if path_taken else []
    self.received_by_all = received_by_all
    self.previous_link = previous_link

    # Cost of the path that the packet takes.    
    self.path_cost = path_cost

  # This is the function that triggers the 'received_by_all' callback function.
  def packet_received_by_all(self, transmitted_time):
    self.received_by_all(self.packet_id, (transmitted_time - self.transmit_start_time))

class Link(object):
  # 'first_router' and 'second_router' are references to the routers being connected by a particular link.
  # 'line' is the representation of the connection (the 'wire').
  def __init__(self, link_id, first_router, second_router, transmittion_time, env):
    self.link_id = link_id
    self.first_router = first_router
    self.second_router = second_router
    self.transmittion_time = transmittion_time
    self.env = env
    self.line = simpy.Resource(env, capacity = 1)
  
  def transmit_packet(self, sender_id, packet):
    with self.line.request() as line:
      yield line 
      destination_router = self.second_router if sender_id == self.first_router.router_id else self.first_router
      yield self.env.timeout(self.transmittion_time)
      packet.path_cost += self.transmittion_time
      self.env.process(destination_router.handle_packet(packet, packet_priority = 0))

class Router(object):
  def __init__(self, router_id, env, poisson_mean, num_packets):
    self.router_id = router_id
    self.env = env
    self.router_links = []
    self.poisson_mean = poisson_mean
    self.num_packets = num_packets
    self.num_packets_delivered = 0
    self.packet_queue = simpy.PriorityResource(self.env, capacity = 1)

    # These are the packets that have been sucessfully transmitted.
    self.packets = {}
    self.env.process(self.generate_packet())    

  def generate_packet(self):
    packet_count = 1
    while packet_count <= self.num_packets:
      arrival_time = poisson.rvs(self.poisson_mean)
      yield self.env.timeout(arrival_time)
      packet = Packet(packet_count, self.router_id, self.env.now, self.packet_delivered_to_all, None, None, None, 0)
      self.env.process(self.handle_packet(packet, packet_count))
      packet_count += 1

  def handle_packet(self, packet, packet_priority):
    with self.packet_queue.request(packet_priority) as req:
      yield req
      if self.router_id not in packet.path_taken:
        self.init_transmission(packet)

  # This function initialized the transmission of a packet using a link's 'transmit_packet' function.
  def init_transmission(self, packet):
    # This variable is used to flag whether or not the packet we are attempting to transmit was created at this router.
    is_my_packet = True if packet.source == self.router_id else False

    if self.router_id not in packet.visited_routers:
      packet.visited_routers.append(self.router_id)
    packet.path_taken.append(self.router_id)

    # If this is my packet or if it took the shortest path to get to me.
    if is_my_packet or self.check_if_shortest_path(packet):
      # If a packet has been to all the routers.
      if len(packet.visited_routers) == 10:
        packet.packet_received_by_all(self.env.now)
      else:
        for link in self.router_links:
          if link.link_id != packet.previous_link:
            # Doing a deep copy of the path taken to ensure that each new instance of the packet has it's own path.
            packet_to_transmit = Packet(packet.packet_id, packet.source, packet.transmit_start_time, packet.received_by_all, packet.visited_routers, copy.deepcopy(packet.path_taken), link.link_id, packet.path_cost)
            self.env.process(link.transmit_packet(self.router_id, packet_to_transmit))
 
  def check_if_shortest_path(self, packet):
    packet_info = [packet.path_taken[-2], packet.path_cost]
    return packet_info == get_shortest_path(packet.source, self.router_id)
      
  # This is a callback function that will be passed on to the packet. Triggered when packet received by all routers.
  def packet_delivered_to_all(self, packet_id, transmit_time):
    if packet_id not in self.packets:
      self.packets[packet_id] = transmit_time
      self.num_packets_delivered += 1

# This function returns the shortest paths from a router to all other routers.
def get_shortest_path(source_router, current_router):
  # 'source_router' denotes the origin of the packet.
  # 'current_router' denotes the router that is making the request.
  shortest_paths = {
    # In the lists below, the left element is the router on the shortest path and the right element is the cost of the shortest path.
    0 : {
      1 : [8, 6],
      2 : [8, 9],
      3 : [8, 5],
      4 : [8, 8],
      5 : [6, 9],
      6 : [6, 4],
      7 : [8, 3],
      8 : [8, 2],
      9 : [9, 3],    
    },
    1 : {
      0 : [3, 6],
      2 : [3, 5],
      3 : [3, 1],
      4 : [4, 2],
      5 : [3, 8],
      6 : [3, 6],
      7 : [3, 3],
      8 : [3, 4],
      9 : [3, 8],    
    },
    2 : {
      0 : [3, 9],
      1 : [3, 5],
      3 : [3, 4],
      4 : [3, 7],
      5 : [5, 3],
      6 : [5, 8],
      7 : [3, 6],
      8 : [3, 7],
      9 : [5, 10],    
    },
    3 : {
      0 : [7, 5],
      1 : [1, 1],
      2 : [2, 4],
      4 : [4, 3],
      5 : [2, 7],
      6 : [7, 5],
      7 : [7, 2],
      8 : [7, 3],
      9 : [7, 7],    
    },
    4 : {
      0 : [3, 8],
      1 : [1, 2],
      2 : [3, 7],
      3 : [3, 3],
      5 : [3, 10],
      6 : [3, 8],
      7 : [3, 5],
      8 : [3, 6],
      9 : [3, 10],    
    },
    5 : {
      0 : [6, 9],
      1 : [2, 8],
      2 : [2, 3],
      3 : [2, 7],
      4 : [2, 10],
      6 : [6, 5],
      7 : [6, 8],
      8 : [6, 9],
      9 : [6, 7],    
    },
    6 : {
      0 : [0, 4],
      1 : [7, 6],
      2 : [5, 8],
      3 : [7, 5],
      4 : [7, 8],
      5 : [5, 5],
      7 : [7, 3],
      8 : [7, 4],
      9 : [9, 2],    
    },
    7 : {
      0 : [8, 3],
      1 : [3, 3],
      2 : [3, 6],
      3 : [3, 2],
      4 : [3, 5],
      5 : [6, 8],
      6 : [6, 3],
      8 : [8, 1],
      9 : [6, 5],     
    },
    8 : {
      0 : [0, 2],
      1 : [7, 4],
      2 : [7, 7],
      3 : [7, 3],
      4 : [7, 6],
      5 : [7, 9],
      6 : [7, 4],
      7 : [7, 1],
      9 : [0, 5],    
    },
    9 : {
      0 : [0, 3],
      1 : [6, 8],
      2 : [6, 10],
      3 : [6, 7],
      4 : [6, 10],
      5 : [6, 7],
      6 : [6, 2],
      7 : [6, 5],
      8 : [0, 5],    
    },    
  }
  return shortest_paths[current_router][source_router]

if __name__ == "__main__":
  num_routers = 10
  num_packets = 10
  poisson_mean = 20
  total_transmit_times = []
  env = simpy.Environment()
  routers = [Router(router_id, env, poisson_mean, num_packets) for router_id in range(num_routers)]

  link06 = Link(0, routers[0], routers[6], 4, env)
  link08 = Link(1, routers[0], routers[8], 2, env)
  link09 = Link(2, routers[0], routers[9], 3, env)
  link13 = Link(3, routers[1], routers[3], 1, env)
  link14 = Link(4, routers[1], routers[4], 2, env)
  link23 = Link(5, routers[2], routers[3], 4, env)
  link25 = Link(6, routers[2], routers[5], 3, env)
  link34 = Link(7, routers[3], routers[4], 3, env)
  link37 = Link(8, routers[3], routers[7], 2, env)
  link56 = Link(9, routers[5], routers[6], 5, env)
  link67 = Link(10, routers[6], routers[7], 3, env)
  link68 = Link(11, routers[6], routers[8], 6, env)
  link69 = Link(12, routers[6], routers[9], 2, env)
  link78 = Link(13, routers[7], routers[8], 1, env)

  for router in routers:
    # Adding the links to each router.
    if router.router_id == 0:
      router.router_links.append(link06)
      router.router_links.append(link08)
      router.router_links.append(link09)
    elif router.router_id == 1:
      router.router_links.append(link13)
      router.router_links.append(link14)
    elif router.router_id == 2:
      router.router_links.append(link23)
      router.router_links.append(link25)
    elif router.router_id == 3:
      router.router_links.append(link13)
      router.router_links.append(link23)
      router.router_links.append(link34)
      router.router_links.append(link37)
    elif router.router_id == 4:
      router.router_links.append(link14)
      router.router_links.append(link34)
    elif router.router_id == 5:
      router.router_links.append(link25)
      router.router_links.append(link56)
    elif router.router_id == 6:
      router.router_links.append(link06)
      router.router_links.append(link56)
      router.router_links.append(link67)
      router.router_links.append(link68)
      router.router_links.append(link69)
    elif router.router_id == 7:
      router.router_links.append(link37)
      router.router_links.append(link67)
      router.router_links.append(link78)
    elif router.router_id == 8:
      router.router_links.append(link08)
      router.router_links.append(link78)
      router.router_links.append(link68)
    elif router.router_id == 9:
      router.router_links.append(link09)
      router.router_links.append(link69)
        
  env.run()
  for router in routers:
    mean = sum(router.packets.values())/len(router.packets)
    total_transmit_times.append(mean)
    print("Router %d: Mean Transmit Time: %.2f, Packets Delivered: %d" % (router.router_id, mean, router.num_packets_delivered))
  print
  print("Overall System Mean Transmit Time: %.2f" % (np.mean(total_transmit_times)))
