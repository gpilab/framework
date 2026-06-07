#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# syntax.py
'''Syntax highlighting from:
    https://wiki.python.org/moin/PyQt/Python%20syntax%20highlighting
'''

from gpi import QtCore, QtGui, QtWidgets

# QRegExp was removed in Qt6; use QRegularExpression instead.
# qtpy exposes whichever is available, with a compatibility shim for Qt5.
try:
    QRegularExpression = QtCore.QRegularExpression
    _USE_REGULAR_EXPRESSION = True
except AttributeError:
    QRegExp = QtCore.QRegExp          # Qt5 fallback
    _USE_REGULAR_EXPRESSION = False

QColor = QtGui.QColor
QTextCharFormat = QtGui.QTextCharFormat
QFont = QtGui.QFont
QSyntaxHighlighter = QtGui.QSyntaxHighlighter


def _make_re(pattern):
    """Return a compiled regex object compatible with the installed Qt version."""
    if _USE_REGULAR_EXPRESSION:
        return QRegularExpression(pattern)
    return QRegExp(pattern)


def _re_index_in(rx, text, offset=0):
    if _USE_REGULAR_EXPRESSION:
        m = rx.match(text, offset)
        return m.capturedStart() if m.hasMatch() else -1
    return rx.indexIn(text, offset)


def _re_matched_length(rx, text, offset=0):
    if _USE_REGULAR_EXPRESSION:
        m = rx.match(text, offset)
        return m.capturedLength() if m.hasMatch() else 0
    return rx.matchedLength()


def _re_pos(rx, nth):
    """Return the start position of the nth capture (Qt5 only helper)."""
    if _USE_REGULAR_EXPRESSION:
        return -1   # not used in QRegularExpression path
    return rx.pos(nth)


def _re_cap(rx, nth):
    """Return the nth capture string (Qt5 only helper)."""
    if _USE_REGULAR_EXPRESSION:
        return ""
    return rx.cap(nth)


def format(color, style='', bkgnd=None):
    """Return a QTextCharFormat with the given attributes.
    """
    _color = QColor()
    _color.setNamedColor(color)
    if bkgnd:
        _bkgnd_color = QColor()
        _bkgnd_color.setNamedColor(bkgnd)

    _format = QTextCharFormat()
    _format.setForeground(_color)
    if bkgnd:
        _format.setBackground(_bkgnd_color)
    if 'bold' in style:
        _format.setFontWeight(QFont.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)

    return _format


# Syntax styles that can be shared by all languages
STYLES = {
    'keyword': format('blue'),
    'operator': format('red'),
    'brace': format('darkGray'),
    'defclass': format('black', 'bold'),
    'string': format('magenta'),
    'string2': format('darkMagenta'),
    'comment': format('darkGreen', 'italic'),
    'self': format('black', 'italic'),
    'numbers': format('brown'),
    'tab': format('white', bkgnd='lightGray')
}


class PythonHighlighter (QSyntaxHighlighter):
    """Syntax highlighter for the Python language.
    """
    # Python keywords
    keywords = [
        'and', 'assert', 'break', 'class', 'continue', 'def',
        'del', 'elif', 'else', 'except', 'exec', 'finally',
        'for', 'from', 'global', 'if', 'import', 'in',
        'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'yield',
        'None', 'True', 'False',
    ]

    # Python operators
    operators = [
        '=',
        # Comparison
        '==', '!=', '<', '<=', '>', '>=',
        # Arithmetic
        r'\+', '-', r'\*', '/', '//', r'\%', r'\*\*',
        # In-place
        r'\+=', '-=', r'\*=', '/=', r'\%=',
        # Bitwise
        r'\^', r'\|', r'\&', r'\~', '>>', '<<',
    ]

    # Python braces
    braces = [
        r'\{', r'\}', r'\(', r'\)', r'\[', r'\]',
    ]

    # white space
    spaces = [
        '\t',
    ]

    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        # Multi-line strings (expression, in_state, style)
        self.tri_single = (_make_re("'''"), 1, STYLES['string2'])
        self.tri_double = (_make_re('"""'), 2, STYLES['string2'])

        rules = []

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, STYLES['keyword'])
                  for w in PythonHighlighter.keywords]
        rules += [(r'%s' % o, 0, STYLES['operator'])
                  for o in PythonHighlighter.operators]
        rules += [(r'%s' % b, 0, STYLES['brace'])
                  for b in PythonHighlighter.braces]
        rules += [(r'%s' % q, 0, STYLES['tab'])
                  for q in PythonHighlighter.spaces]

        # All other rules
        rules += [
            (r'\bself\b', 0, STYLES['self']),
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, STYLES['string']),
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, STYLES['string']),
            (r'\bdef\b\s*(\w+)', 1, STYLES['defclass']),
            (r'\bclass\b\s*(\w+)', 1, STYLES['defclass']),
            (r'#[^\n]*', 0, STYLES['comment']),
            (r'\b[+-]?[0-9]+[lL]?\b', 0, STYLES['numbers']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, STYLES['numbers']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, STYLES['numbers']),
        ]

        self.rules = [(_make_re(pat), index, fmt) for (pat, index, fmt) in rules]

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        for expression, nth, fmt in self.rules:
            index = _re_index_in(expression, text, 0)
            while index >= 0:
                if _USE_REGULAR_EXPRESSION:
                    m = expression.match(text, index)
                    pos = m.capturedStart(nth) if nth else m.capturedStart()
                    length = m.capturedLength(nth) if nth else m.capturedLength()
                else:
                    expression.indexIn(text, index)
                    pos = _re_pos(expression, nth)
                    length = len(_re_cap(expression, nth))
                if length == 0:
                    break
                self.setFormat(pos, length, fmt)
                index = _re_index_in(expression, text, index + length)

        self.setCurrentBlockState(0)

        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.tri_double)

    def match_multiline(self, text, delimiter, in_state, style):
        """Highlight multi-line triple-quoted strings.

        Returns True if the block ends while still inside the string.
        """
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        else:
            start = _re_index_in(delimiter, text)
            add = _re_matched_length(delimiter, text) if start >= 0 else 0

        while start >= 0:
            end = _re_index_in(delimiter, text, start + add)
            ml = _re_matched_length(delimiter, text, start + add)
            if end >= add:
                length = end - start + add + ml
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            self.setFormat(start, length, style)
            start = _re_index_in(delimiter, text, start + length)

        return self.currentBlockState() == in_state
