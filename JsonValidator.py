# -*- coding: utf-8 -*-
#############################################################################
# Author  : Jerome ODIER
#
# Email   : jerome.odier@lpsc.in2p3.fr
#
# Version : 1.0 beta (2013)
#
#############################################################################

import os, jsonv.JsonParser, jsonv.ExprParser

#############################################################################

class JsonValidatorError(Exception):
	pass

#############################################################################

class Validator(jsonv.JsonParser.Parser):
	#####################################################################

	def __init__(self, s, verbose = False):
		#############################################################
		# CONSTRUCTOR						    #
		#############################################################

		jsonv.JsonParser.Parser.__init__(self, s)

		self.verbose = verbose

		self.entry = Rule(None, None, None, None, None)

		self.RULES = {
		}

		self.RULE_KEYS = {
		}

		#############################################################
		# CHECK HEADER						    #
		#############################################################

		if len(self.root.pairs) != 1:
			raise JsonValidatorError('error: line `%d`: bad grammar' % self.root.line)

		#############################################################

		pair1 = list(self.root.pairs)[0]

		if pair1.key != 'grammar':
			raise JsonValidatorError('error: line `%d`: missing key `grammar`' % pair1.line)

		if pair1.value.type != pair1.value.TYPE_OBJECT:
			raise JsonValidatorError('error: line `%d`: missing object `grammar`' % pair1.line)

		#############################################################
		# CREATE RULES						    #
		#############################################################

		for pair2 in pair1.value.object.pairs:
			rule_type = pair2.key

			#####################################################
			# ENTRY POINT					    #
			#####################################################

			if rule_type == 'entry':
				if pair2.value.type != pair2.value.TYPE_STR:
					raise JsonValidatorError('error: line `%d`: invalid entry point' % pair2.line)
				if not self.entry.expr is None:
					print('warning: line `%d`: redefined entry point' % pair2.line)
				self.entry.expr = pair2.value.value

				self.entry.line = pair2.line

				continue

			#####################################################
			# PAIRS & VALUES				    #
			#####################################################

			if not rule_type in ['pair', 'value'] or pair2.value.type != pair2.value.TYPE_OBJECT:
				raise JsonValidatorError('error: line `%d`: invalid rule `%s`' % (pair2.line, rule_type))

			#####################################################
			# GET PARAMETERS				    #
			#####################################################

			rule_name = None
			rule_expr = None
			json_key  = None
			json_type = None

			line = pair2.line

			for pair3 in pair2.value.object.pairs:
				#############################################
				# RULE					    #
				#############################################

				if   pair3.key == 'rule':
					if pair3.value.type != pair2.value.TYPE_STR:
						raise JsonValidatorError('error: line `%d`: invalid type for pair `rule`' % pair3.line)
					if not rule_name is None:
						print('warning: line `%d`: redefined pair `rule`' % pair3.line)
					rule_name = pair3.value.value

				#############################################
				# KEY					    #
				#############################################

				elif pair3.key == 'key':
					if pair3.value.type != pair2.value.TYPE_STR:
						raise JsonValidatorError('error: line `%d`: invalid type for pair `key`' % pair3.line)
					if not json_key is None:
						print('warning: line `%d`: redefined pair `key`' % pair3.line)
					json_key = pair3.value.value

				#############################################
				# TYPE					    #
				#############################################

				elif pair3.key == 'type':
					if pair3.value.type != pair2.value.TYPE_STR:
						raise JsonValidatorError('error: line `%d`: invalid type for pair `type`' % pair3.line)
					if not json_type is None:
						print('warning: line `%d`: redefined pair `type`' % pair3.line)
					json_type = pair3.value.value

				#############################################
				# ::=					    #
				#############################################

				elif pair3.key == '::=':
					if pair3.value.type != pair2.value.TYPE_STR:
						raise JsonValidatorError('error: line `%d`: invalid type for pair `::=`' % pair3.line)
					if rule_expr is None:
						rule_expr = '(%s)' % pair3.value.value
					else:
						rule_expr += '|(%s)' % pair3.value.value

					line = pair3.line

				#############################################

				else:
					raise JsonValidatorError('error: line `%d`: invalid key `%s`' % (pair3.line, pair3.key))

			#####################################################
			# CHECK PARAMETERS				    #
			#####################################################

			if rule_name is None:
				raise JsonValidatorError('error: line `%d`: undefined name for rule `%s`' % (pair2.line, rule_name))

			if json_type is None:
				raise JsonValidatorError('error: line `%d`: undefined type for rule `%s`' % (pair2.line, rule_name))

			#####################################################

			if not json_type in ['object', 'array', 'bool', 'flt', 'str']:
				raise JsonValidatorError('error: line `%d`: invalid type `%s` for rule `%s`' % (pair2.line, json_type, rule_name))

			#####################################################

			if rule_type in ['pair']:
				if json_key is None:
					raise JsonValidatorError('error: line `%d`: undefined key for rule `%s`' % (pair2.line, rule_name))

			if json_type in ['object', 'array']:
				if rule_expr is None:
					raise JsonValidatorError('error: line `%d`: undefined ::= for rule `%s`' % (pair2.line, rule_name))

			#####################################################
			# APPEND RULE					    #
			#####################################################

			self.RULES[rule_name] = Rule(
				rule_type,
				rule_name,
				rule_expr,
				json_key,
				json_type,
				line = line
			)

			#####################################################
			# APPEND KEY					    #
			#####################################################

			self.RULE_KEYS[rule_name] = json_key

		#############################################################
		# CHECK ENTRY POINT					    #
		#############################################################

		if self.entry is None:
			raise JsonValidatorError('error: line `%d`: no entry point' % pair1.line)

		#############################################################
		# COMPILE RULES						    #
		#############################################################

		for rule_name in self.RULES:

			if not self.RULES[rule_name].expr is None:

				self.RULES[rule_name].compile(self.RULE_KEYS, verbose = self.verbose)

		#############################################################
		# COMPILE ENTRY POINT					    #
		#############################################################

		self.entry.compile(self.RULE_KEYS, verbose = self.verbose)

		#############################################################
		# VERBOSE MODE						    #
		#############################################################

		if self.verbose:
			print('#############################################################################')
			print('# GRAMMAR                                                                   #')
			print('#############################################################################')

			print('entry: %s' % self.entry.EXPR.__str__())

			for rule_name in self.RULES:
				self.RULES[rule_name].dump()

			print('#############################################################################')

	#####################################################################

	def _validate_pair(self, closure, pair, verbose):
		expected = ','.join(closure)

		if len(expected) == 0:
			expected = 'Ø'

		#############################################################
		# OBJECT						    #
		#############################################################

		if   pair.value.type == jsonv.JsonParser.Value.TYPE_OBJECT:
			#####################################################
			# LOOKUP MATCHING RULE				    #
			#####################################################

			rule = None

			for rule_name in closure:

				RULE = self.RULES[rule_name]

				if RULE.json_type == 'object' and RULE.json_key == pair.key:
					rule = RULE
					break

			if rule is None:
				raise JsonValidatorError('error: line `%d`: no matching rule (among: %s) for pair `%s`' % (pair.line, expected, pair.key))

			#####################################################
			# GET DFA & INITIAL STATE			    #
			#####################################################

			dfa = rule.EXPR.table

			state = dfa.start

			#####################################################
			# VALIDATE					    #
			#####################################################

			for sub_pair in pair.value.object.pairs:
				transitions = dfa.transitions.get(state, dict())

				states = transitions.get(self._validate_pair(transitions.keys(), sub_pair, verbose), None)

				if states is None:
					raise JsonValidatorError('error: line `%d`: unexpected pair `%s` in pair `%s` for rule `%s`' % (sub_pair.line, sub_pair.key, pair.key, rule.name))

				state = iter(states).next()

			if not dfa.isFinalState(state):
				raise JsonValidatorError('error: line `%d`: unexpected end in pair `%s` for rule `%s`' % (pair.line, pair.key, rule.name))

			return rule.name

		#############################################################
		# ARRAY							    #
		#############################################################

		elif pair.value.type == jsonv.JsonParser.Value.TYPE_ARRAY:
			#####################################################
			# LOOKUP MATCHING RULE				    #
			#####################################################

			rule = None

			for rule_name in closure:

				RULE = self.RULES[rule_name]

				if RULE.json_type == 'array' and RULE.json_key == pair.key:
					rule = RULE
					break

			if rule is None:
				raise JsonValidatorError('error: line `%d`: no matching rule (among: %s) for pair `%s`' % (pair.line, expected, pair.key))

			#####################################################
			# GET DFA & INITIAL STATE			    #
			#####################################################

			dfa = rule.EXPR.table

			state = dfa.start

			#####################################################
			# VALIDATE					    #
			#####################################################

			for sub_value in pair.value.array.values:
				transitions = dfa.transitions.get(state, dict())

				states = transitions.get(self._validate_value(transitions.keys(), sub_value, pair.key, verbose), None)

				if states is None:
					raise JsonValidatorError('error: line `%d`: unexpected value `%s` in pair `%s` for rule `%s`' % (sub_value.line, sub_value.getTypeString(), pair.key, rule.name))

				state = iter(states).next()

			if not dfa.isFinalState(state):
				raise JsonValidatorError('error: line `%d`: unexpected end in value `%s` for rule `%s`' % (pair.line, pair.key, rule.name))

			return rule.name

		#############################################################
		# VALUE							    #
		#############################################################

		else:
			#####################################################
			# LOOKUP MATCHING RULE				    #
			#####################################################

			rule = None

			for rule_name in closure:

				RULE = self.RULES[rule_name]

				if RULE.json_type in ['bool', 'flt', 'str'] and RULE.json_key == pair.key:
					rule = RULE
					break

			if rule is None:
				raise JsonValidatorError('error: line `%d`: no matching rule (among: %s) for pair `%s`' % (pair.line, expected, pair.key))

			#####################################################
			# VALIDATE					    #
			#####################################################

			json_type = RULE.json_type
			JSON_TYPE = pair.value.getTypeString()

			if JSON_TYPE == 'null' or json_type == JSON_TYPE:
				return rule.name

			else:
				raise JsonValidatorError('error: line `%d`: type `%s` expected but type `%s` found in pair `%s` for rule `%s`' % (pair.line, json_type, JSON_TYPE, pair.key, rule.name))

	#####################################################################

	def _validate_value(self, closure, value, last_pair_name, verbose):
		expected = ','.join(closure)

		if len(expected) == 0:
			expected = 'Ø'

		#############################################################
		# OBJECT						    #
		#############################################################

		if   value.type == jsonv.JsonParser.Value.TYPE_OBJECT:
			#####################################################
			# LOOKUP MATCHING RULE				    #
			#####################################################

			rule = None

			for rule_name in closure:

				RULE = self.RULES[rule_name]

				if RULE.json_type == 'object':
					rule = RULE
					break

			if rule is None:
				raise JsonValidatorError('error: line `%d`: no matching rule (among: %s) for value of type `%s` from pair `%s`' % (value.line, expected, value.getTypeString(), last_pair_name))

			#####################################################
			# GET DFA & INITIAL STATE			    #
			#####################################################

			dfa = rule.EXPR.table

			state = dfa.start

			#####################################################
			# VALIDATE					    #
			#####################################################

			for sub_pair in value.object.pairs:
				transitions = dfa.transitions.get(state, dict())

				states = transitions.get(self._validate_pair(transitions.keys(), sub_pair, verbose), None)

				if states is None:
					raise JsonValidatorError('error: line `%d`: unexpected pair `%s` in value from pair `%s` for rule `%s`' % (sub_pair.line, sub_pair.key, last_pair_name, rule.name))

				state = iter(states).next()

			if not dfa.isFinalState(state):
				raise JsonValidatorError('error: line `%d`: unexpected end in value from pair `%s` for rule `%s`' % (value.line, last_pair_name, rule.name))

			return rule.name

		#############################################################
		# ARRAY							    #
		#############################################################

		elif value.type == jsonv.JsonParser.Value.TYPE_ARRAY:
			#####################################################
			# LOOKUP MATCHING RULE				    #
			#####################################################

			rule = None

			for rule_name in closure:

				RULE = self.RULES[rule_name]

				if RULE.json_type == 'array':
					rule = RULE
					break

			if rule is None:
				raise JsonValidatorError('error: line `%d`: no matching rule (among: %s) for value of type `%s` from pair `%s`' % (value.line, expected, value.getTypeString(), last_pair_name))

			#####################################################
			# GET DFA & INITIAL STATE			    #
			#####################################################

			dfa = rule.EXPR.table

			state = dfa.start

			#####################################################
			# VALIDATE					    #
			#####################################################

			for sub_value in value.value.array.values:
				transitions = dfa.transitions.get(state, dict())

				states = transitions.get(self._validate_pair(transitions.keys(), sub_value, verbose), None)

				if states is None:
					raise JsonValidatorError('error: line `%d`: unexpected value `%s` in value from pair `%s` for rule `%s`' % (sub_value.line, sub_value.getTypeString(), last_pair_name, rule.name))

				state = iter(states).next()

			if not dfa.isFinalState(state):
				raise JsonValidatorError('error: line `%d`: unexpected end in value from pair `%s` for rule `%s`' % (value.line, last_pair_name, rule.name))

			return rule.name

		#############################################################
		# VALUE							    #
		#############################################################

		else:
			#####################################################
			# LOOKUP MATCHING RULE				    #
			#####################################################

			rule = None

			for rule_name in closure:

				RULE = self.RULES[rule_name]

				if RULE.json_type in ['bool', 'flt', 'str']:
					rule = RULE
					break

			if rule is None:
				raise JsonValidatorError('error: line `%d`: no matching rule (among: %s) for value of type `%s` from pair `%s`' % (value.line, expected, value.getTypeString(), last_pair_name))

			#####################################################
			# VALIDATE					    #
			#####################################################

			json_type = RULE.json_type
			JSON_TYPE = value.getTypeString()

			if JSON_TYPE == 'null' or json_type == JSON_TYPE:
				return rule.name

			else:
				raise JsonValidatorError('error: line `%d`: type `%s` expected but type `%s` found in value from pair `%s` for rule `%s`' % (value.line, json_type, JSON_TYPE, last_pair_name, rule.name))

	#####################################################################

	def validate(self, doc, verbose = False):
		root = doc.root

		#############################################################
		# GET DFA & INITIAL STATE				    #
		#############################################################

		dfa = self.entry.EXPR.table

		state = dfa.start

		#############################################################
		# VALIDATE						    #
		#############################################################

		try:
			for pair in root.pairs:
				transitions = dfa.transitions.get(state, dict())

				states = transitions.get(self._validate_pair(transitions.keys(), pair, verbose), None)

				if states is None:
					raise JsonValidatorError('error: line `%d`: unexpected pair `%s`' % (pair.line, pair.key))

				state = iter(states).next()

			if not dfa.isFinalState(state):
				raise JsonValidatorError('error: line `%d`: unexpected pair `%s`' % (root.line, root.key))

			return True

		except JsonValidatorError, e:

			if verbose:
				print(e.__str__())

			return False

#############################################################################

def parseString(s, verbose = False):

	try:
		return Validator(s, verbose)

	except jsonv.JsonParser.JsonParserError, e:
		raise JsonValidatorError(e.__str__())

#############################################################################

class Rule(object):
	#####################################################################

	def __init__(self, type, name, expr, json_key, json_type, line = 1):
		self.line = line
		self.type = type
		self.name = name

		self.expr = expr
		self.EXPR = None

		self.json_key = json_key
		self.json_type = json_type

	#####################################################################

	def compile(self, rule_keys, verbose = False):

		if not self.expr is None:

			try:
				self.EXPR = jsonv.ExprParser.parseString(self.expr, rule_keys, line = self.line)

				if verbose:
					#####################################
					# GRAPHVIZ			    #
					#####################################

					srcName = '%s.dot' % self.name
					dstName = '%s.pdf' % self.name

					try:
						f = open(srcName, 'w')

					except IOError:
						pass

					else:
						f.write(self.EXPR.table.__str__())

						f.close()

						os.system('dot -Tpdf %s > %s ; rm -f %s' % (srcName, dstName, srcName))

			except jsonv.ExprParser.ExprParserError, e:
				raise JsonValidatorError(e.__str__())

	#####################################################################

	def dump(self):
		print('  %s (json_key: `%s`, json_type: `%s`)' % (self.name, self.json_key, self.json_type))

		if not self.expr is None:
			print('   ::= %s' % self.EXPR.__str__())

#############################################################################
