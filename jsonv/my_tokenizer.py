# -*- coding: utf-8 -*-
#############################################################################
# Author  : Jerome ODIER
#
# Email   : jerome.odier@lpsc.in2p3.fr
#
# Version : 1.0 beta (2013)
#
#############################################################################

class TokenizerError(Exception):
	pass

#############################################################################

def _shift(s, group, line):
	result = len(group[0])

	while True:
		idx = s.find(group[1], result)

		if idx < 0:
			raise TokenizerError('syntax error, line `%d`, missing token `%s`' % (line, group[1]))

		result = idx + len(group[1])

		if s[idx - 1] != '\\':
			break

	return result

#############################################################################

def tokenize(s, spaces = [], symbols = [], strings = [], line = 1):
	s = unicode(s)

	result_tokens = []
	result_lines = []

	i = 0x0000
	l = len(s)

	word = ''

	while i < l:
		#############################################################
		# LINES							    #
		#############################################################

		if s[i] == '\n':
			line += 1

		#############################################################
		# SAPCES						    #
		#############################################################

		if s[i] in spaces:

			if len(word) > 0 :
				result_tokens.append(word)
				result_lines.append(line)
				word = ''

			i += 1

			continue

		#############################################################
		# SYMBOLS						    #
		#############################################################

		found = False

		for symbol in symbols:

			if s[i: ].startswith(symbol):

				if len(word) > 0 :
					result_tokens.append(word)
					result_lines.append(line)
					word = ''

				j = i + len(symbol)

				result_tokens.append(s[i: j])
				result_lines.append(line)

				i = j

				found = True
				break

		if found:
			continue

		#############################################################
		# STRINGS						    #
		#############################################################

		found = False

		for string in strings:

			if s[i: ].startswith(string[0]):

				if len(word) > 0 :
					result_tokens.append(word)
					result_lines.append(line)
					word = ''

				j = i + _shift(s[i: ], string, line)

				result_tokens.append(s[i: j])
				result_lines.append(line)

				i = j

				found = True
				break

		if found:
			continue

		#############################################################

		word += s[i]
		i += 1

	#####################################################################

	if len(word) > 0 :
		result_tokens.append(word)
		result_lines.append(line)

	return result_tokens, result_lines

#############################################################################
