#############################################################################
# Author  : Jerome ODIER
#
# Email   : jerome.odier@lpsc.in2p3.fr
#
# Version : 1.0 beta (2013)
#
#############################################################################
# EBNF grammar (from `http://www.json.org/`):
#   object ::= { members? }
#   members ::= pair (, members)?
#   pair ::= str : value
#   array ::= [ elements? ]
#   elements ::= value (, elements)?
#   value ::= object | array | null | true | false | flt | str
#############################################################################

import sys, jsonv.my_tokenizer

#############################################################################

class JsonParserError(Exception):
	pass

#############################################################################

def isFlt(s):

	try:
		float(s)

		return True

	except ValueError:
		return False

#############################################################################

def isStr(s):
	return s[0] == '\'' or s[0] == '\"'

#############################################################################

def getType(s):

	if   s == 'null':
		result = Value.TYPE_NULL
	elif s == 'true':
		result = Value.TYPE_TRUE
	elif s == 'false':
		result = Value.TYPE_FALSE
	elif isFlt(s):
		result = Value.TYPE_FLT
	elif isStr(s):
		result = Value.TYPE_STR
	else:
		result = -1

	return result

#############################################################################

class Tokenizer(object):
	#####################################################################

	LBRACE = 0
	RBRACE = 1
	LBRACKET = 2
	RBRACKET = 3
	COLON = 4
	COMMA = 5

	#####################################################################

	def __init__(self, s, line = 1):

		try:
			self.tokens, self.lines = jsonv.my_tokenizer.tokenize(s, spaces = [' ', '\t', '\n'], symbols = ['{', '}', '[', ']', ':', ','], strings = [['\'', '\''], ['\"', '\"']], line = line)

			self.types = []

			self.i = 0

		except jsonv.my_tokenizer.TokenizerError, e:
			raise JsonParserError(e.__str__())

		for i in xrange(len(self.tokens)):

			token = self.tokens[i]
			line = self.lines[i]

			if   token == '{':
				self.types.append(Tokenizer.LBRACE)
			elif token == '}':
				self.types.append(Tokenizer.RBRACE)
			elif token == '[':
				self.types.append(Tokenizer.LBRACKET)
			elif token == ']':
				self.types.append(Tokenizer.RBRACKET)
			elif token == ':':
				self.types.append(Tokenizer.COLON)
			elif token == ',':
				self.types.append(Tokenizer.COMMA)
			else:
				TYPE = getType(token)

				if TYPE >= 0:
					self.types.append(TYPE)
				else:
					if sys.platform in ['win32', 'win64']:
						raise JsonParserError('syntax error, line `%d`, unexpected token `%s`' % (line, token))
					else:
						raise JsonParserError('syntax error, line `%d`, \033[31munexpected token `%s`\033[0m' % (line, token))

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

	def __init__(self, s, line = 1):
		self.tokenizer = Tokenizer(s, line)

		self.root = self.parseObject()

		if self.root is None:
			self.error('missing root object')

	#####################################################################
	#   object ::= { members? }
	#####################################################################

	def parseObject(self):
		L = set([])

		if not self.tokenizer.hasNext() or self.tokenizer.peekType() != Tokenizer.LBRACE:
			return None

		line = self.tokenizer.peekLine()
		self.tokenizer.next()

		self.parseMembers(L)

		if not self.tokenizer.hasNext() or self.tokenizer.peekType() != Tokenizer.RBRACE:
			self.error('missing `}`')

		self.tokenizer.next()

		return Object(L, line = line)

	#####################################################################
	#   members ::= pair (, members)?
	#####################################################################

	def parseMembers(self, L):

		while True:
			pair = self.parsePair()

			if pair is None:
				break

			L.add(pair)

			if not self.tokenizer.hasNext() or self.tokenizer.peekType() != Tokenizer.COMMA:
				break

			self.tokenizer.next()

	#####################################################################
	#   pair ::= str : value
	#####################################################################

	def parsePair(self):
		#########
		#  STR  #
		#########

		if not self.tokenizer.hasNext() or self.tokenizer.peekType() != Value.TYPE_STR:
			return None

		line = self.tokenizer.peekLine()
		str = self.tokenizer.next()

		#########
		#   :   #
		#########

		if not self.tokenizer.hasNext() or self.tokenizer.peekType() != Tokenizer.COLON:
			self.error('missing `:`')

		self.tokenizer.next()

		#########
		# VALUE #
		#########

		value = self.parseValue()

		if value is None:
			self.error('missing value')

		#########

		return Pair(str, value, line = line)

	#####################################################################
	#   array ::= [ elements? ]
	#####################################################################

	def parseArray(self):
		L = list([])

		if not self.tokenizer.hasNext() or self.tokenizer.peekType() != Tokenizer.LBRACKET:
			return None

		line = self.tokenizer.peekLine()
		self.tokenizer.next()

		self.parseElements(L)

		if not self.tokenizer.hasNext() or self.tokenizer.peekType() != Tokenizer.RBRACKET:
			self.error('missing `]`')

		self.tokenizer.next()

		return Array(L, line = line)

	#####################################################################
	#   elements ::= value (, elements)?
	#####################################################################

	def parseElements(self, L):

		while True:
			value = self.parseValue()

			if value is None:
				break

			L.append(value)

			if not self.tokenizer.hasNext() or self.tokenizer.peekType() != Tokenizer.COMMA:
				break

			self.tokenizer.next()

	#####################################################################
	#   value ::= object | array | null | true | false | flt | str
	#####################################################################

	def parseValue(self):

		if not self.tokenizer.hasNext():
			self.error('truncated json data')

		line = self.tokenizer.peekLine()

		##############
		# PRIMITIVES #
		##############

		type = self.tokenizer.peekType()

		if type in [Value.TYPE_NULL, Value.TYPE_TRUE, Value.TYPE_FALSE, Value.TYPE_FLT, Value.TYPE_STR]:
			return Value(type, value = self.tokenizer.next(), line = line)

		###########
		# OBJECTS #
		###########

		object = self.parseObject()

		if not object is None:
			return Value(Value.TYPE_OBJECT, object = object, line = line)

		##########
		# ARRAYS #
		##########

		array = self.parseArray()

		if not array is None:
			return Value(Value.TYPE_ARRAY, array = array, line = line)

		########

		return None

	#####################################################################

	def error(self, s):

		if sys.platform in ['win32', 'win64']:
			raise JsonParserError('syntax error, line `%d`, %s' % (self.tokenizer.peekLine(), s))
		else:
			raise JsonParserError('syntax error, line `%d`, \033[31m%s\033[0m' % (self.tokenizer.peekLine(), s))

	#####################################################################

	def to_python(self):
		return self.root.to_python()

	#####################################################################

	def to_string(self):
		return self.root.to_string()

	#####################################################################

	__str__ = to_string

#############################################################################

def parseString(s, line = 1):
	return Parser(s, line = line)

#############################################################################

class Object(object):
	#####################################################################

	def __init__(self, pairs, line = 1):
		self.line = line
		self.pairs = pairs

	#####################################################################

	def to_python(self):
		result = {}

		for pair in self.pairs:
			result.update(pair.to_python())

		return result

	#####################################################################

	def to_string(self):
		return '{' + ','.join(pair.to_string() for pair in self.pairs) + '}'

	#####################################################################

	__str__ = to_string

#############################################################################

class Array(object):
	#####################################################################

	def __init__(self, values, line = 1):
		self.line = line
		self.values = values

	#####################################################################

	def to_python(self):
		result = []

		for value in self.values:
			result.append(value.to_python())

		return result

	#####################################################################

	def to_string(self):
		return '[' + ','.join(value.to_string() for value in self.values) + ']'

	#####################################################################

	__str__ = to_string

#############################################################################

class Pair(object):
	#####################################################################

	def __init__(self, key, value, line = 1):
		self.line = line

		if key[0] == '\'' or key[0] == '\"':
			key = key[+1: ]
			key = key[: -1]

		self. key  =  key
		self.value = value

	#####################################################################

	def __hash__(self):
		return self.key.__hash__()

	#####################################################################

	def to_python(self):
		return {self.key: self.value.to_python()}

	#####################################################################

	def to_string(self):
		return '"%s":%s' % (self.key, self.value)

	#####################################################################

	__str__ = to_string

#############################################################################

class Value(object):
	#####################################################################

	TYPE_OBJECT = 100
	TYPE_ARRAY = 101
	TYPE_FLT = 102
	TYPE_STR = 103
	TYPE_TRUE = 104
	TYPE_FALSE = 105
	TYPE_NULL = 106

	#####################################################################

	def __init__(self, type, object = None, array = None, value = None, line = 1):
		self.line = line
		self.type = type
		self.object = object
		self.array = array

		if self.type == self.TYPE_STR and (value[0] == '\'' or value[0] == '\"'):
			value = value[+1: ]
			value = value[: -1]

			value = value.replace('\\\'', '\'')
			value = value.replace('\\\"', '\"')

			value = value.replace('\\\\', '\\')
			value = value.replace('\\/', '/')

			value = value.replace('\\b', '\b')
			value = value.replace('\\f', '\f')
			value = value.replace('\\n', '\n')
			value = value.replace('\\r', '\r')
			value = value.replace('\\t', '\t')

		self.value = value

	#####################################################################

	def getTypeString(self):

		if   self.type == Value.TYPE_OBJECT:
			result = 'object'
		elif self.type == Value.TYPE_ARRAY:
			result = 'array'
		elif self.type == Value.TYPE_FLT:
			result = 'flt'
		elif self.type == Value.TYPE_STR:
			result = 'str'
		elif self.type == Value.TYPE_TRUE:
			result = 'bool'
		elif self.type == Value.TYPE_FALSE:
			result = 'bool'
		else:
			result = 'null'

		return result

	#####################################################################

	def to_python(self):

		if   self.type == Value.TYPE_OBJECT:
			result = self.object.to_python()
		elif self.type == Value.TYPE_ARRAY:
			result = self.array.to_python()
		elif self.type == Value.TYPE_FLT:

			try:
				result = int(self.value)

			except ValueError:
				result = float(self.value)

		elif self.type == Value.TYPE_STR:
			result = self.value
		elif self.type == Value.TYPE_TRUE:
			result = True
		elif self.type == Value.TYPE_FALSE:
			result = False
		else:
			result = None

		return result

	#####################################################################

	def to_string(self):
		if   self.type == self.TYPE_OBJECT:
			return self.object.to_string()
		elif self.type == self.TYPE_ARRAY:
			return self.array.to_string()
		elif self.type == self.TYPE_STR:
			return '"%s"' % self.value
		else:
			return self.value

	#####################################################################

	__str__ = to_string

#############################################################################
