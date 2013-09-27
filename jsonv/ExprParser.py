# -*- coding: utf-8 -*-
#############################################################################
# Author  : Jerome ODIER
#
# Email   : jerome.odier@lpsc.in2p3.fr
#
# Version : 1.0 beta (2013)
#
#############################################################################
# EBNF grammar:
#   expression ::= term ( `|` term )+
#   term ::= suffix ( `,` suffix )+
#   suffix ::= factor ('?' | '+' | '*')
#   factor ::= `(` expression `)`
#   factor ::= RULE
#############################################################################

import sys, jsonv.nfa, jsonv.my_tokenizer

#############################################################################

class ExprParserError(Exception):
	pass

#############################################################################

class RefValue(object):
	def __init__(self):
		self.value = 0

#############################################################################

def isIdent(s):

	for c in s:

		if c.isalnum() == False and c != '_':
			return False

	return True

#############################################################################

def getType(s):

	if   isIdent(s):
		result = Node.ELEMENT_RULE
	else:
		result = -1

	return result

#############################################################################

class Tokenizer(object):
	#####################################################################

	LPAREN = 0
	RPAREN = 1

	#####################################################################

	def __init__(self, s, line = 1):
		self.tokens, self.lines = jsonv.my_tokenizer.tokenize(s, spaces = [' ', '\t'], symbols = ['|', ',', '?', '+', '*', '(', ')'], line = line)

		self.types = []

		self.i = 0

		for i in xrange(len(self.tokens)):

			token = self.tokens[i]
			line = self.lines[i]

			if   token == '|':
				self.types.append(Node.ELEMENT_VB)
			elif token == ',':
				self.types.append(Node.ELEMENT_COMMA)
			elif token == '?':
				self.types.append(Node.ELEMENT_OPT)
			elif token == '+':
				self.types.append(Node.ELEMENT_PLUS)
			elif token == '*':
				self.types.append(Node.ELEMENT_STAR)
			elif token == '(':
				self.types.append(Tokenizer.LPAREN)
			elif token == ')':
				self.types.append(Tokenizer.RPAREN)
			else:
				TYPE = getType(token)

				if TYPE >= 0:
					self.types.append(TYPE)
				else:
					if sys.platform in ['win32', 'win64']:
						raise ExprParserError('syntax error, line `%d`, unexpected token `%s`' % (line, token))
					else:
						raise ExprParserError('syntax error, line `%d`, \033[31munexpected token `%s`\033[0m' % (line, token))

	#####################################################################

	def hasNext(self):
		return self.i < len(self.tokens)

	#####################################################################

	def next(self):
		result = self.tokens[self.i]

		self.i += 1

		return result

	#####################################################################

	def peekToken(self):
		return self.tokens[self.i]

	#####################################################################

	def peekType(self):
		return self.types[self.i]

	#####################################################################

	def peekLine(self):

		if self.hasNext():
			return self.lines[self.i - 0]
		else:
			return self.lines[self.i - 1]

	#####################################################################

	def isOccurrenceIndicator(self):
		return self.types[self.i] in [Node.ELEMENT_OPT, Node.ELEMENT_PLUS, Node.ELEMENT_STAR]

#############################################################################

class Parser(object):
	#####################################################################

	def __init__(self, s, rule_keys, line = 1):
		self.tokenizer = Tokenizer(s, line = line)

		if self.tokenizer.hasNext():
			self.root = self.parseExpression(rule_keys)

			self.table = self.dfa()

		else:
			self.error('emtpy regular expression')

	#####################################################################

	def parseExpression(self, rule_keys):
		#############################################################
		# expression ::= term ( `|` term )+			    #
		#############################################################

		left = self.parseTerm(rule_keys)

		if self.tokenizer.hasNext() and self.tokenizer.peekType() == Node.ELEMENT_VB:

			node = Node(Node.ELEMENT_VB)
			self.tokenizer.next()

			right = self.parseExpression(rule_keys)

			node.nodeLeft = left
			node.nodeRight = right

			left = node

		return left

	#####################################################################

	def parseTerm(self, rule_keys):
		#############################################################
		# term ::= suffix ( `,` suffix )+			    #
		#############################################################

		left = self.parseSuffix(rule_keys)

		if self.tokenizer.hasNext() and self.tokenizer.peekType() == Node.ELEMENT_COMMA:

			node = Node(Node.ELEMENT_COMMA)
			self.tokenizer.next()

			right = self.parseTerm(rule_keys)

			node.nodeLeft = left
			node.nodeRight = right

			left = node

		return left

	#####################################################################

	def parseSuffix(self, rule_keys):
		#############################################################
		# suffix ::= factor ('?' | '+' | '*')			    #
		#############################################################

		left_and_right = self.parseFactor(rule_keys)

		if self.tokenizer.hasNext() and self.tokenizer.isOccurrenceIndicator():

			node = Node(self.tokenizer.peekType())
			self.tokenizer.next()

			node.nodeLeft = left_and_right
			node.nodeRight = left_and_right

			return node

		else:
			return left_and_right

	#####################################################################

	def parseFactor(self, rule_keys):
		#############################################################
		# factor ::= `(` expression `)`				    #
		#############################################################

		if self.tokenizer.hasNext() and self.tokenizer.peekType() == Tokenizer.LPAREN:
			self.tokenizer.next()

			expression = self.parseExpression(rule_keys)

			if self.tokenizer.hasNext() and self.tokenizer.peekType() == Tokenizer.RPAREN:
				self.tokenizer.next()

				return expression

			self.error('`)` expected, but got `%s`' % self.tokenizer.next())

		#############################################################
		# factor ::= RULE					    #
		#############################################################

		if self.tokenizer.hasNext() and self.tokenizer.peekType() == Node.ELEMENT_RULE:

			node = Node(Node.ELEMENT_RULE)

			node.nodeValue = self.tokenizer.next()

			if not node.nodeValue in rule_keys:
				raise self.error('undefined rule `%s`' % (node.nodeValue))

			return node

		#############################################################

		self.error('factor expected')

	#####################################################################

	def error(self, s):

		if sys.platform in ['win32', 'win64']:
			raise ExprParserError('syntax error, line `%d`, %s' % (self.tokenizer.peekLine(), s))
		else:
			raise ExprParserError('syntax error, line `%d`, \033[31m%s\033[0m' % (self.tokenizer.peekLine(), s))

	#####################################################################

	def _nfa(self, dfa, cnt, OLD_STATE0, NEW_STATE0, node):
		#############################################################
		# `|` operator						    #
		#############################################################

		if   node.nodeType == Node.ELEMENT_VB:
			cnt.value += 1

			OLD_STATE1, NEW_STATE1 = self._nfa(dfa, cnt, OLD_STATE0, cnt.value, node.nodeLeft)

			cnt.value += 0

			OLD_STATE2, NEW_STATE2 = self._nfa(dfa, cnt, OLD_STATE0, cnt.value, node.nodeRight)

			return OLD_STATE1, NEW_STATE2

		#############################################################
		# `,` operator						    #
		#############################################################

		elif node.nodeType == Node.ELEMENT_COMMA:
			cnt.value += 1

			OLD_STATE1, NEW_STATE1 = self._nfa(dfa, cnt, OLD_STATE0, cnt.value, node.nodeLeft)

			cnt.value += 1

			OLD_STATE2, NEW_STATE2 = self._nfa(dfa, cnt, NEW_STATE1, cnt.value, node.nodeRight)

			return OLD_STATE1, NEW_STATE2

		#############################################################
		# `?` operator						    #
		#############################################################

		elif node.nodeType == Node.ELEMENT_OPT:
			cnt.value += 1

			OLD_STATE1, NEW_STATE1 = self._nfa(dfa, cnt, OLD_STATE0, cnt.value, node.nodeLeft)

			dfa.addTransition(OLD_STATE1, jsonv.nfa.epsilon, NEW_STATE1)

			return OLD_STATE1, NEW_STATE1

		#############################################################
		# `+` operator						    #
		#############################################################

		elif node.nodeType == Node.ELEMENT_PLUS:
			cnt.value += 1

			OLD_STATE1, NEW_STATE1 = self._nfa(dfa, cnt, OLD_STATE0, cnt.value, node.nodeLeft)

			cnt.value += 1

			dfa.addTransition(NEW_STATE1, jsonv.nfa.epsilon, cnt.value)
			dfa.addTransition(NEW_STATE1, jsonv.nfa.epsilon, cnt.value)

			tokens = dfa.transitions[OLD_STATE0]

			for token in tokens:

				new_states = dfa.transitions[OLD_STATE0][token]

				for new_state in new_states:

					if new_state == NEW_STATE1:
						dfa.addTransition(NEW_STATE1, token, NEW_STATE1)

			return OLD_STATE1, cnt.value

		#############################################################
		# `*` operator						    #
		#############################################################

		elif node.nodeType == Node.ELEMENT_STAR:
			cnt.value += 1

			OLD_STATE1, NEW_STATE1 = self._nfa(dfa, cnt, OLD_STATE0, cnt.value, node.nodeLeft)

			cnt.value += 1

			dfa.addTransition(OLD_STATE1, jsonv.nfa.epsilon, cnt.value)
			dfa.addTransition(NEW_STATE1, jsonv.nfa.epsilon, cnt.value)

			tokens = dfa.transitions[OLD_STATE0]

			for token in tokens:

				new_states = dfa.transitions[OLD_STATE0][token]

				for new_state in new_states:

					if new_state == NEW_STATE1:
						dfa.addTransition(NEW_STATE1, token, NEW_STATE1)

			return OLD_STATE1, cnt.value

		#############################################################
		# terminal (RULE)					    #
		#############################################################

		elif node.nodeType == Node.ELEMENT_RULE:
			dfa.addTransition(OLD_STATE0, node.nodeValue, NEW_STATE0)

			return OLD_STATE0, NEW_STATE0

	#####################################################################

	def dfa(self):
		result = jsonv.nfa.Nfa(0)

		if self.root.nodeType != Node.ELEMENT_RULE:
			result.addFinalState(self._nfa(result, RefValue(), 0, 0, self.root)[1])
		else:
			result.addFinalState(self._nfa(result, RefValue(), 0, 1, self.root)[1])

		return result.to_dfa()

	#####################################################################

	def __str__(self):
		return self.root.__str__()

#############################################################################

def parseString(s, rule_keys, line = 1):
	return Parser(s, rule_keys, line = line)

#############################################################################

class Node(object):
	#####################################################################

	ELEMENT_VB = 100
	ELEMENT_COMMA = 101
	ELEMENT_OPT = 102
	ELEMENT_PLUS = 103
	ELEMENT_STAR = 104
	ELEMENT_RULE = 105

	#####################################################################

	def __init__(self, nodeType, nodeValue = None, level = -1):
		self.nodeType = nodeType
		self.nodeValue = nodeValue
		self.nodeLeft = None
		self.nodeRight = None

	#####################################################################

	def __str__(self):

		if   self.nodeType == self.ELEMENT_VB:
			return '`|`(%s, %s)' % (self.nodeLeft.__str__(), self.nodeRight.__str__())
		elif self.nodeType == self.ELEMENT_COMMA:
			return '`&`(%s, %s)' % (self.nodeLeft.__str__(), self.nodeRight.__str__())
		elif self.nodeType == self.ELEMENT_OPT:
			return '`?`(%s)' % (self.nodeLeft.__str__())
		elif self.nodeType == self.ELEMENT_PLUS:
			return '`+`(%s)' % (self.nodeLeft.__str__())
		elif self.nodeType == self.ELEMENT_STAR:
			return '`*`(%s)' % (self.nodeLeft.__str__())
		elif self.nodeType == self.ELEMENT_RULE:
			return self.nodeValue

#############################################################################
