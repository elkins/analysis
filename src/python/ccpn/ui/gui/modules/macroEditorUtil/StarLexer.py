#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2025-02-14 17:36:58 +0000 (Fri, February 14, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-11-11 21:43:35 +0000 (Mon, November 11, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from pygments.lexer import RegexLexer
from pygments.token import Keyword, Name, Number, String, Whitespace, Comment, Generic, Literal, Operator


class StarLexer(RegexLexer):
    """
    Pygments lexer for STAR-based formats like  NEF (NMR Exchange Format).

    """
    name = 'STAR'
    aliases = ['star', 'bmrb', 'nef']
    filenames = ['*.str', '*.nef', '*.bmrb'] # although .bmrb is unlikely usually they don't have extension
    tokens = {
        'root': [
            # Comments
            (r'#.*$', Comment.Single),  # Single-line comments
            (r';.*?;', Comment.Multiline),  # Multiline comments (semicolon blocks)

            # Block Identifiers (save_ and loop_ as purple)
            (r'\b(save_[a-zA-Z0-9_]*)\b', Generic.Subheading),  # save_ blocks
            (r'\b(loop_|stop_)\b', Keyword),  # loop_ and stop_

            # Field Name (black)
            (r'(_[a-zA-Z0-9_.]+)(\s+)', Name),  # Field names

            # Floats (blue) - only one dot (also allows scientific notation)
            (r'(\-?\d+\.\d+([eE][-+]?\d+)?)', Number),  # Match floats
            (r'(\-?\d+)', Number),  # Match integers

            # Strings, including datetime format, are treated as string
            (r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?)', String),

            # Match multiple dots as strings (e.g., 3.2.0 or other mixed values)
            (r'(\-?\d+\.\d+\.\d+)', String),  # Multiple dots treated as string

            # Strings (green) - any non-numeric value or non-datetime value
            (r'([^\s#;0-9\.\-][^\s#;]*)', String),  # Match strings

            # Booleans
            (r'\b(true|false)\b', Keyword),  # Match true/false as keywords

            # Whitespace handling
            (r'\s+', Whitespace),  # Whitespace handling
            ]
        }

