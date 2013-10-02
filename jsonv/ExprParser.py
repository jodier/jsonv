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

	def add_and_fetch(self, value = 1):
		self.value += value

		return self.value

#############################################################################

def isIdent(s):

	for c in s:

		if c.isalnum() == False and c != '_':
			return False

	return True

#############################################################################

def getType(s):

	if   isIdent(s):
		result = Node.NODE_TYPE_RULE
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
				self.types.append(Node.NODE_TYPE_IOR)
			elif token == ',':
				self.types.append(Node.NODE_TYPE_AND)
			elif token == '?':
				self.types.append(Node.NODE_TYPE_OPT)
			elif token == '+':
				self.types.append(Node.NODE_TYPE_PLUS)
			elif token == '*':
				self.types.append(Node.NODE_TYPE_STAR)
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

#############################################################################

class Parser(object):
	#####################################################################

	def __init__(self, s, rule_keys, line = 1):

		if len(s.strip()) > 0:
			self.tokenizer = Tokenizer(s, line = line)

			self.root = self.parseExpression(rule_keys)
		else:
			self.root = ((((((((((((((None))))))))))))))

		self.table = self.dfa()

	#####################################################################

	def parseExpression(self, rule_keys):
		#############################################################
		# expression ::= term ( `|` term )+			    #
		#############################################################

		left = self.parseTerm(rule_keys)

		if self.tokenizer.hasNext() and Node.isIor(self.tokenizer.peekType()):

			node = Node(Node.NODE_TYPE_IOR)
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

		i = 0

		suffixes = {}

		while True:
			key = None

			suffix = self.parseSuffix(rule_keys)

			if suffix is None:
				break

			if   Node.isRule(suffix.nodeType):
				key = rule_keys.get(suffix         .nodeValue)
			elif Node.isOcOp(suffix.nodeType):
				key = rule_keys.get(suffix.nodeLeft.nodeValue)

			if key is None:
				key = str(i)
				i += 1

			suffixes[key] = suffix

			if self.tokenizer.hasNext() and Node.isAnd(self.tokenizer.peekType()):
				self.tokenizer.next()
			else:
				break

		#############################################################

		left = None

		for suffix_name in suffixes:

			if left is None:
				left = suffixes[suffix_name]
			else:
				node = Node(Node.NODE_TYPE_AND)

				right = suffixes[suffix_name]

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

		if self.tokenizer.hasNext() and Node.isOcOp(self.tokenizer.peekType()):

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

		if self.tokenizer.hasNext() and Node.isRule(self.tokenizer.peekType()):

			node = Node(Node.NODE_TYPE_RULE)

			node.nodeValue = self.tokenizer.next()

			if not node.nodeValue in rule_keys:
				raise self.error('undefined rule `%s`' % (node.nodeValue))

			return node

		#############################################################

		self.error('rule expected')

	#####################################################################

	def error(self, s):

		if sys.platform in ['win32', 'win64']:
			raise ExprParserError('syntax error, line `%d`, %s' % (self.tokenizer.peekLine(), s))
		else:
			raise ExprParserError('syntax error, line `%d`, \033[31m%s\033[0m' % (self.tokenizer.peekLine(), s))

	#####################################################################

	def _nfa(self, automata, cnt, FROM, node, VERS):
		#############################################################
		# `|` operator						    #
		#############################################################

		if   node.nodeType == Node.NODE_TYPE_IOR:
			self._nfa(automata, cnt, FROM, node.nodeLeft, VERS)
			self._nfa(automata, cnt, FROM, node.nodeRight, VERS)

		#############################################################
		# `,` operator						    #
		#############################################################

		elif node.nodeType == Node.NODE_TYPE_AND:
			TMP1 = cnt.add_and_fetch()

			self._nfa(automata, cnt, FROM, node.nodeLeft, TMP1)
			self._nfa(automata, cnt, TMP1, node.nodeRight, VERS)

		#############################################################
		# `?` operator						    #
		#############################################################

		elif node.nodeType == Node.NODE_TYPE_OPT:
			TMP1 = cnt.add_and_fetch()

			automata.addTransition(FROM, jsonv.nfa.epsilon, TMP1)

			self._nfa(automata, cnt, TMP1, node.nodeRight, VERS)

			automata.addTransition(TMP1, jsonv.nfa.epsilon, VERS)

		#############################################################
		# `+` operator						    #
		#############################################################

		elif node.nodeType == Node.NODE_TYPE_PLUS:
			TMP1 = cnt.add_and_fetch()

			self._nfa(automata, cnt, FROM, node.nodeRight, TMP1)

			self._nfa(automata, cnt, TMP1, node.nodeRight, TMP1)

			automata.addTransition(TMP1, jsonv.nfa.epsilon, VERS)

		#############################################################
		# `*` operator						    #
		#############################################################

		elif node.nodeType == Node.NODE_TYPE_STAR:
			TMP1 = cnt.add_and_fetch()

			automata.addTransition(FROM, jsonv.nfa.epsilon, TMP1)

			self._nfa(automata, cnt, TMP1, node.nodeRight, TMP1)

			automata.addTransition(TMP1, jsonv.nfa.epsilon, VERS)

		#############################################################
		# terminal (RULE)					    #
		#############################################################

		elif node.nodeType == Node.NODE_TYPE_RULE:
			automata.addTransition(FROM, node.nodeValue, VERS)

	#####################################################################

	def dfa(self):
		cnt = RefValue()

		result = jsonv.nfa.Nfa(0)

		if not self.root is None:

			if not self.root is None and self.root.nodeType != Node.NODE_TYPE_RULE:

				tmp = cnt.add_and_fetch(value = 1)
				self._nfa(result, cnt, 0, self.root, tmp)
				result.addFinalState(tmp)

			else:
				tmp = cnt.add_and_fetch(value = 0)
				self._nfa(result, cnt, 0, self.root, 0x0)
				result.addFinalState(0x0)

		else:
			result.addFinalState(0x0)

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

	NODE_TYPE_IOR = 100
	NODE_TYPE_AND = 101
	NODE_TYPE_OPT = 102
	NODE_TYPE_PLUS = 103
	NODE_TYPE_STAR = 104
	NODE_TYPE_RULE = 105

	#####################################################################

	@staticmethod
	def isAnd(nodeType):
		return nodeType in [Node.NODE_TYPE_AND]

	#####################################################################

	@staticmethod
	def isIor(nodeType):
		return nodeType in [Node.NODE_TYPE_IOR]

	#####################################################################

	@staticmethod
	def isOcOp(nodeType):
		return nodeType in [Node.NODE_TYPE_OPT,
				    Node.NODE_TYPE_PLUS,
				    Node.NODE_TYPE_STAR]

	#####################################################################

	@staticmethod
	def isRule(nodeType):
		return nodeType in [Node.NODE_TYPE_RULE]

	#####################################################################

	def __init__(self, nodeType, nodeValue = None):
		self.nodeType = nodeType
		self.nodeValue = nodeValue
		self.nodeLeft = None
		self.nodeRight = None

	#####################################################################

	def __str__(self):

		if   self.nodeType == self.NODE_TYPE_IOR:
			return '`|`(%s, %s)' % (self.nodeLeft.__str__(), self.nodeRight.__str__())
		elif self.nodeType == self.NODE_TYPE_AND:
			return '`&`(%s, %s)' % (self.nodeLeft.__str__(), self.nodeRight.__str__())
		elif self.nodeType == self.NODE_TYPE_OPT:
			return '`?`(%s)' % (self.nodeLeft.__str__())
		elif self.nodeType == self.NODE_TYPE_PLUS:
			return '`+`(%s)' % (self.nodeLeft.__str__())
		elif self.nodeType == self.NODE_TYPE_STAR:
			return '`*`(%s)' % (self.nodeLeft.__str__())
		elif self.nodeType == self.NODE_TYPE_RULE:
			return self.nodeValue

#############################################################################
