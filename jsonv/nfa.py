#############################################################################
# Author  : Jerome ODIER
#
# Email   : jerome.odier@lpsc.in2p3.fr
#
# Version : 1.0 beta (2013)
#
#############################################################################

epsilon = '_eps'

#############################################################################

class Nfa(object):
	#####################################################################

	def __init__(self, start):
		self.start = start

		self.transitions = dict()
		self.alphabet = set()
		self.final = set()

	#####################################################################

	def addTransition(self, old_state, token, new_state):
		#############################################################

		if self.transitions.get(old_state) is None:
			self.transitions[old_state] = dict()

		#############################################################

		if self.transitions[old_state].get(token) is None:
			self.transitions[old_state][token] = set()

		#############################################################

		self.transitions[old_state][token].add(new_state)

		self.alphabet.add(token)

	#####################################################################

	def addFinalState(self, state):
		self.final.add(state)

	#####################################################################

	def isFinalState(self, state):
		return state in self.final

	#####################################################################

	def epsilonClosure(self, state):
		result1 = {state}
		result2 = 0x00000

		while True:
			found = False

			for state in result1:

				if not self.transitions.get(state) is None and not self.transitions[state].get(epsilon) is None:

					l1 = len(result1)
					result1 = result1.union(self.transitions[state][epsilon])
					l2 = len(result1)

					if l1 != l2:
						found = True

			if found == False:

				for state in sorted(result1):
					result2 = 10 * result2 + state

				result2 *= 100

				return result2, result1

	#####################################################################

	def to_dfa(self):
		todo = {}
		done = {}
		temp = {}

		#############################################################
		# INITIAL CASE						    #
		#############################################################

		closure_state, closure_states = self.epsilonClosure(self.start)

		#############################################################

		result = Nfa(closure_state)

		todo[closure_state] = closure_states

		for state in closure_states:

			if self.isFinalState(state):
				result.addFinalState(closure_state)

		#############################################################
		# LOOP OVER NEW STATES					    #
		#############################################################

		while len(todo) > 0:

			for todo_state in todo:
				old_states = todo[todo_state]

				#############################################
				# LOOP OVER TRANSITIONS			    #
				#############################################

				for old_state in old_states:
					transition_tokens = self.transitions.get(old_state, dict())

					for transition_token in transition_tokens:
						new_states = transition_tokens.get(transition_token, set())

						if transition_token != epsilon:

							for new_state in new_states:
								closure_state, closure_states = self.epsilonClosure(new_state)

								if not closure_state in done:
									#####################
									# ADD TRANSITION    #
									#####################

									result.addTransition(todo_state, transition_token, closure_state)

									temp[closure_state] = closure_states

									#####################
									# ADD FINAL STATES  #
									#####################

									for state in closure_states:

										if self.isFinalState(state):
											result.addFinalState(closure_state)

			#####################################################

			done.update(todo)
			todo = {}
			todo.update(temp)
			temp = {}

		#############################################################

		return result

	#####################################################################

	def __str__(self):
		#############################################################

		result = 'digraph {\n  rankdir = "LR";\n'

		#############################################################

		old_states = sorted(self.transitions)

		#############################################################
		# LOOP OVER TRANSITIONS					    #
		#############################################################

		for old_state in old_states:
			tokens = sorted(self.transitions[old_state])

			for token in tokens:
				new_states = sorted(self.transitions[old_state][token])

				for new_state in new_states:

					if token == epsilon:
						token = '&epsilon;'

					result += '  "%d" -> "%d" [label = "%s"];\n' % (old_state, new_state, token)

		#############################################################
		# INITIAL STATE						    #
		#############################################################

		result += '  "nothing" -> "%d";\n' % self.start

		#############################################################
		# FINAL STATES						    #
		#############################################################

		for state in sorted(self.final):
			result += '  "%d" [shape = "doublecircle"];\n' % state

		#############################################################

		return result + '}\n'

#############################################################################
