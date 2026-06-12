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
'''Syntax highlighting for the Python language.
Ported from QRegExp (Qt5) to QRegularExpression (Qt6).
'''

from gpi import QtCore, QtGui

QRegularExpression = QtCore.QRegularExpression
QColor = QtGui.QColor
QTextCharFormat = QtGui.QTextCharFormat
QFont = QtGui.QFont
QSyntaxHighlighter = QtGui.QSyntaxHighlighter


def format(color, style='', bkgnd=None):
    """Return a QTextCharFormat with the given attributes."""
    _color = QColor()
    _color.setNamedColor(color)
    _format = QTextCharFormat()
    _format.setForeground(_color)
    if bkgnd:
        _bkgnd_color = QColor()
        _bkgnd_color.setNamedColor(bkgnd)
        _format.setBackground(_bkgnd_color)
    if 'bold' in style:
        _format.setFontWeight(QFont.Weight.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)
    return _format


STYLES = {
    'keyword':  format('blue'),
    'operator': format('red'),
    'brace':    format('darkGray'),
    'defclass': format('black', 'bold'),
    'string':   format('magenta'),
    'string2':  format('darkMagenta'),
    'comment':  format('darkGreen', 'italic'),
    'self':     format('black', 'italic'),
    'numbers':  format('brown'),
    'tab':      format('white', bkgnd='lightGray'),
}


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for the Python language."""

    keywords = [
        'and', 'assert', 'break', 'class', 'continue', 'def',
        'del', 'elif', 'else', 'except', 'exec', 'finally',
        'for', 'from', 'global', 'if', 'import', 'in',
        'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'yield',
        'None', 'True', 'False',
    ]

    operators = [
        r'=',
        r'==', r'!=', r'<', r'<=', r'>', r'>=',
        r'\+', r'-', r'\*', r'/', r'//', r'\%', r'\*\*',
        r'\+=', r'-=', r'\*=', r'/=', r'\%=',
        r'\^', r'\|', r'\&', r'\~', r'>>', r'<<',
    ]

    braces = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']
    spaces = [r'\t']

    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        # Multi-line string delimiters: (QRegularExpression, state_id, style)
        self.tri_single = (QRegularExpression(r"'''"), 1, STYLES['string2'])
        self.tri_double = (QRegularExpression(r'"""'), 2, STYLES['string2'])

        rules = []
        rules += [(r'\b%s\b' % w, 0, STYLES['keyword'])
                  for w in PythonHighlighter.keywords]
        rules += [(r'%s' % o, 0, STYLES['operator'])
                  for o in PythonHighlighter.operators]
        rules += [(r'%s' % b, 0, STYLES['brace'])
                  for b in PythonHighlighter.braces]
        rules += [(r'%s' % q, 0, STYLES['tab'])
                  for q in PythonHighlighter.spaces]
        rules += [
            (r'\bself\b',                              0, STYLES['self']),
            (r'"[^"\\]*(\\.[^"\\]*)*"',               0, STYLES['string']),
            (r"'[^'\\]*(\\.[^'\\]*)*'",               0, STYLES['string']),
            (r'\bdef\b\s*(\w+)',                       1, STYLES['defclass']),
            (r'\bclass\b\s*(\w+)',                     1, STYLES['defclass']),
            (r'#[^\n]*',                               0, STYLES['comment']),
            (r'\b[+-]?[0-9]+[lL]?\b',                 0, STYLES['numbers']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b',     0, STYLES['numbers']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b',
             0, STYLES['numbers']),
        ]

        self.rules = [(QRegularExpression(pat), index, fmt)
                      for (pat, index, fmt) in rules]

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        for expression, nth, fmt in self.rules:
            offset = 0
            while True:
                match = expression.match(text, offset)
                if not match.hasMatch():
                    break
                start = match.capturedStart(nth)
                length = match.capturedLength(nth)
                if start < 0 or length <= 0:
                    # Advance past the overall match to avoid infinite loop
                    advance = match.capturedLength(0)
                    offset = match.capturedStart(0) + (advance if advance > 0 else 1)
                    continue
                self.setFormat(start, length, fmt)
                offset = match.capturedStart(0) + match.capturedLength(0)

        self.setCurrentBlockState(0)

        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            self.match_multiline(text, *self.tri_double)

    def match_multiline(self, text, delimiter, in_state, style):
        """Highlight multi-line triple-quoted strings.

        Returns True if we're still inside a multi-line string at end of block.
        """
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        else:
            m = delimiter.match(text)
            if m.hasMatch():
                start = m.capturedStart()
                add = m.capturedLength()
            else:
                return False

        while start >= 0:
            m_end = delimiter.match(text, start + add)
            if m_end.hasMatch():
                end = m_end.capturedStart()
                length = end - start + add + m_end.capturedLength()
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            self.setFormat(start, length, style)
            m_next = delimiter.match(text, start + length)
            if m_next.hasMatch():
                start = m_next.capturedStart()
                add = m_next.capturedLength()
            else:
                break

        return self.currentBlockState() == in_state
