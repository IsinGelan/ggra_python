
from typing import Any

class Graph:
	"""can sadly not detect whether a graph is cyclic"""
	def __init__(self):
		self.graph = dict()

	def add_edge(self, u, v):
		if u not in self.graph:
			self.graph[u] = []
		if v not in self.graph:
			self.graph[v] = []
		self.graph[u].append(v)

	def sort_for_node(self, v: Any, visited: dict[Any, bool], stack: list):
		visited[v] = True
		for connection in self.graph[v]:
			if not visited[connection]:
				self.sort_for_node(connection, visited, stack)
		stack.append(v)

	def topological_sort(self) -> list:
		visited = {key:False for key in self.graph}
		stack   = []

		for vertex in visited:
			if not visited[vertex]:
				self.sort_for_node(vertex, visited, stack)

		return stack[::-1]
