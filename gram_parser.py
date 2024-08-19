
from typing import Iterator, TextIO

from .ggra_errors import GgraParserError
from .custom_token import Token
from .gram_lexer import token_lines
from .helpers import alltrue, anytrue, index_where, time_info
from .structures import (
    Change, 
    Condition, 
    ConditionEq,
    ConditionNeq, 
    ElementNonterminal, 
    ElementString,
    ExpressionChoice,
    ExpressionIdentifier,
    ExpressionString,
    Nt,
    NtDefinition,
    Pattern, 
    PatternBNForm,
    PatternFrom,
    PatternIf,
    PatternWith,
    SourceChoice, 
    SourceIdentifier, 
    SourceNonterminal,
    SourceString,
    With
)
from .lines import (
    Line,
    LineBNPattern,
    LineChange,
    LineCondition,
    LineFileNt,
    LineFullFrom,
    LineFullNt, 
    LineFullWith, 
    LineOpenFrom, 
    LineOpenNt, 
    LineOpenWith
)

# ================================
LineIterator = Iterator[tuple[int, list[Token]]]

def line_iterator(text: str) -> LineIterator:
    """Returns Iterator of all lines with line number."""
    return enumerate(token_lines(text))

def remove_all_spaces(tokens: list[Token]) -> list[Token]:
    """Removes all Spaces Tokens"""
    return [token for token in tokens if token.name not in ["spaces", "comment"]]

def indent_size(line: list[Token]) -> int:
    if len(line) == 0:
        return 0
    if line[0].name != "spaces":
        return 0
    return len(line[0].content)

def trivial_line(line: list[Token]) -> bool:
    if len(line) == 0:
        return True
    match remove_all_spaces(line):
        case []:
            return True
        case [tok_comment] if tok_comment.name == "comment":
            return True
    return False

def fits_nt_opening(tokens: list[Token]) -> bool:
    """Whether tokens can constitute the header line of a Nt-Definition"""
    if len(tokens) < 3:
        return False # must have at least (, ), :
    if not tokens[0].name == "open_paren":
        return False
    close_p_index = index_where(tokens, lambda token: token.name == "close_paren")
    if close_p_index is None:
        return False
    if len(tokens) < close_p_index:
        return False # no colon would fit after the definition
    # if not tokens[close_p_index+1].name == "colon":
    #     return False
    return True

def nt_opening_params(tokens: list[Token]) -> list[str]:
    if len(tokens) == 0:
        return []
    param_names = []
    for i, token in enumerate(tokens):
        if i % 2 == 0 and token.name != "identifier":
            raise GgraParserError(
                "Parser: Resolving parameters of Nonterminal Definition",
                ["identifier expected", f"got token of type {token.name!r}"]
            )
        if i % 2 == 1 and token.name != "comma":
            raise GgraParserError(
                "Parser: Resolving parameters of Nonterminal Definition",
                ["comma separation expected", f"got token of type {token.name!r}"]
            )
        if i % 2 == 0:
            param_names.append(token.content)
    return param_names

def fits_change(tokens: list[Token]) -> bool:
    """Whether tokens constitute a Change-description"""
    for token in tokens:
        if token.name in [
            "arrow_double",
            "arrow_labeled"
        ]:
            return True
    return False

def fits_or_block(tokens: list[Token]) -> bool:
    """Whether tokens could be an or block for SourceChoice or ExpressionChoice (e.g. identif | "a" | string)"""
    for i, token in enumerate(tokens):
        if i % 2 == 0 and token.name not in ["string", "identifier"]:
            return False
        if i % 2 == 1 and token.name != "or":
            return False
    return True

def or_source_options(tokens: list[Token]) -> SourceChoice:
    options = []
    for i, token in enumerate(tokens):
        if i % 2 == 1:
            continue
        if token.name == "string":
            options.append(SourceString(token.content[1:-1]))
            continue
        if token.name == "identifier":
            options.append(SourceIdentifier(token.content))
        # no support für Nonterminal.param | ... yet
    return SourceChoice(options)

def or_condition_options(tokens: list[Token]) -> ExpressionChoice:
    options = []
    for i, token in enumerate(tokens):
        if i % 2 == 1:
            continue
        if token.name == "string":
            options.append(ExpressionString(token.content[1:-1]))
            continue
        if token.name == "identifier":
            options.append(ExpressionIdentifier(token.content))
    return ExpressionChoice(options)

# ================================
def make_lines(lines: LineIterator) -> Iterator[Line]:
    for i, line_tokens in lines:
        if trivial_line(line_tokens):
            continue
        indent = indent_size(line_tokens)
        spaceless = remove_all_spaces(line_tokens)
        line = partial_parse_line(indent, spaceless)
        yield line

def partial_parse_line(indent: int, line: list[Token]) -> Line:
    match line:
        case [t_from, t_colon, *rest] if alltrue(
            t_from.name == "identifier",
            t_from.content == "from",
            t_colon.name == "colon"
        ):
            if rest:
                return LineFullFrom(indent, parse_bn_pattern(rest))
            return LineOpenFrom(indent)
        case [t_with, t_colon, *rest] if alltrue(
            t_with.name == "identifier",
            t_with.content == "with",
            t_colon.name == "colon"
        ):
            if rest:
                change = parse_change(rest)
                return LineFullWith(indent, With([change]))
            return LineOpenWith(indent)
        case [t_if, *rest] if alltrue(
            t_if.name == "identifier",
            t_if.content == "if"
        ):
            if not rest:
                raise GgraParserError(
                    "Parser: Pre-Parsing lines",
                    ["If expects condition", "However, none was given"]
                )
            return LineCondition(
                indent,
                parse_condition(rest)
            )
        case [t_id, t_arr, t_filename] if alltrue(
            t_id.name == "identifier",
            t_arr.name == "arrow_normal",
            t_filename.name == "string"
        ):
            return LineFileNt(indent, t_id.content, set(), t_filename.content[1:-1])
        case [t_id, t_colon, *rest] if alltrue(
            t_id.name == "identifier",
            t_colon.name == "colon"
        ):
            if rest:
                return LineFullNt(indent, t_id.content, set(), parse_bn_pattern(rest))
            return LineOpenNt(indent, t_id.content, set())
        case changeline if fits_change(changeline):
            return LineChange(
                indent,
                parse_change(changeline)
            )
        case [t_patternstart, *rest] if anytrue(
            t_patternstart.name == "nonterminal",
            t_patternstart.name == "string",
            t_patternstart.name == "epsilon"
        ):
            return LineBNPattern(
                indent,
                parse_bn_pattern(line)
            )
        case [t_id, *rest, t_arr, t_filename] if alltrue(
            t_id.name == "identifier",
            t_arr.name == "arrow_normal",
            t_filename.name == "string",
            fits_nt_opening(rest)
        ):
            close_b_index = index_where(rest, lambda token: token.name == "close_paren")
            param_names = nt_opening_params(rest[1:close_b_index])
            return LineFileNt(indent, t_id.content, set(param_names), t_filename.content[1:-1])
        case [t_id, *rest] if alltrue(
            t_id.name == "identifier",
            fits_nt_opening(rest)
        ):
            close_b_index = index_where(rest, lambda token: token.name == "close_paren")
            param_names = nt_opening_params(rest[1:close_b_index])
            after_header = rest[close_b_index+2:]
            if after_header:
                return LineFullNt(indent, t_id.content, set(param_names), parse_bn_pattern(after_header))
            return LineOpenNt(indent, t_id.content, set(param_names))
        case otherwise:
            raise GgraParserError(
                "Parser: Pre-Parsing lines",
                ["Could not parse line consisting of tokens:", str(otherwise)]
            )

def parse_bn_pattern(line: list[Token]) -> PatternBNForm:
    elements = []
    for token in line:
        if token.name == "string":
            obj = ElementString(token.content[1:-1])
            elements.append(obj)
            continue
        if token.name == "nonterminal":
            obj = ElementNonterminal(token.content[1:-1].replace(" ", ""))
            elements.append(obj)
            continue
        if token.name == "epsilon":
            continue
        raise GgraParserError(
            "Parser: Parsing pattern in Backus-Naur format",
            ["wrong token in pattern:", token.name, "in line", str(line)]
        )
    return PatternBNForm(elements)

def parse_condition(tokens: list[Token]) -> Condition:
    eq_index = index_where(tokens, lambda token: token.name == "equals")
    if eq_index is not None:
        return parse_condition_eq(tokens, eq_index)
    
    neq_index = index_where(tokens, lambda token: token.name == "nequals")
    if neq_index is not None:
        return parse_condition_neq(tokens, neq_index)
    
    match tokens:
        case [t_expr] if t_expr.name == "string":
            return ExpressionString(t_expr.content[1:-1])
        case [t_expr] if t_expr.name == "identifier":
            return ExpressionIdentifier(t_expr.content)
        case otherwise:
            if fits_or_block(otherwise):
                return or_condition_options(otherwise)
            raise GgraParserError(
                "Parser: Parsing condition",
                ["Expression or subexpression expected,", "does not understand", str(otherwise)]
            )
    
def parse_condition_eq(tokens: list[Token], eq_index: int) -> ConditionEq:
    before, after = tokens[:eq_index], tokens[eq_index+1:]
    return ConditionEq(
        parse_condition(before),
        parse_condition(after)
    )

def parse_condition_neq(tokens: list[Token], neq_index: int) -> ConditionNeq:
    before, after = tokens[:neq_index], tokens[neq_index+1:]
    return ConditionNeq(
        parse_condition(before),
        parse_condition(after)
    )

def parse_change(tokens: list[Token]) -> Change:
    match tokens:
        case [t_id1, t_larrow, t_id2] if alltrue(
            t_id1.name == "identifier",
            t_id2.name == "identifier",
            t_larrow.name == "arrow_labeled"
        ):
            # Subject ==person=> Verb
            param   = t_larrow.content[2:-2].strip()
            source  = SourceNonterminal(t_id1.content, param)
            return Change(source, t_id2.content, param)
        case [t_param, t_arrow, t_id1, t_dot, t_id2] if alltrue(
            t_id1.name == "identifier",
            t_id2.name == "identifier",
            t_param.name == "identifier",
            t_arrow.name == "arrow_double",
            t_dot.name == "dot"
        ):
            # genus => Noun.genus
            source  = SourceIdentifier(t_param.content)
            return Change(source, t_id1.content, t_id2.content)
        case [t_str, t_arrow, t_id1, t_dot, t_id2] if alltrue(
            t_id1.name == "identifier",
            t_id2.name == "identifier",
            t_str.name == "string",
            t_arrow.name == "arrow_double",
            t_dot.name == "dot"
        ):
            # "accusative" => Noun.case
            source  = SourceString(t_str.content[1:-1])
            return Change(source, t_id1.content, t_id2.content)
        case [t_id11, t_dot1, t_id12, t_arrow, t_id21, t_dot2, t_id22] if alltrue(
            t_id11.name == "identifier",
            t_id12.name == "identifier",
            t_id21.name == "identifier",
            t_id22.name == "identifier",
            t_arrow.name == "arrow_double",
            t_dot1.name == "dot",
            t_dot2.name == "dot"
        ):
            # Subject.person => Verb.pers
            source  = SourceNonterminal(t_id11.content, t_id12.content)
            return Change(source, t_id21.content, t_id22.content)
        case [*before_arrow, t_arrow, t_id1, t_dot, t_id2] if alltrue(
            t_id1.name == "identifier",
            t_id2.name == "identifier",
            t_arrow.name == "arrow_double",
            t_dot.name == "dot"
        ):
            if not fits_or_block(before_arrow):
                raise GgraParserError(
                    "Parser: Parsing change (line in 'with:')",
                    ["Before change arrow", "Cannot understand pattern:", str(before_arrow)]
                )
            source = or_source_options(before_arrow)
            return Change(source, t_id1.content, t_id2.content)
        case otherwise:
            raise GgraParserError(
                "Parser: Parsing change (line in 'with:')",
                ["Cannot understand pattern:", str(otherwise)]
            )


# ================================
def is_opening(line: Line) -> bool:
    """Whether a line is the opening line of a block"""
    return type(line) in [
        LineOpenFrom,
        LineOpenNt,
        LineOpenWith
    ]

def handle_line_context(contexts: list[tuple[int, list]], line: Line):
    """Appends line to the upmost context
    and appends new context to the layers, if line opens new block"""
    if is_opening(line):
        contexts.append([None, [line]])
        return
    structures = contexts[-1][1]
    structures.append(line)

def group_pattern_def(structures: list[LineBNPattern|PatternFrom|With|LineFullWith|LineCondition]) -> Iterator[list[Line|PatternFrom|With]]:
    """Glues together all contextually related blocks, made up of Pattern and Withs and Conditions"""
    remaining = structures.copy()
    current_group = []
    for structure in remaining:
        if isinstance(structure, (LineBNPattern, PatternFrom)) and current_group != []:
            yield current_group
            current_group = []
        current_group.append(structure)
    yield current_group

#-----------------------
def parse_group(group: list[LineBNPattern|PatternFrom|With|LineFullWith|LineCondition]) -> Pattern:
    current = group[0] if isinstance(group[0], PatternFrom) else PatternBNForm(group[0].content.elements)

    for obj in group[1:]:
        if isinstance(obj, With):
            current = PatternWith(current, obj)
            continue
        if isinstance(obj, LineFullWith):
            current = PatternWith(current, obj.changes)
            continue
        if isinstance(obj, LineCondition):
            current = PatternIf(current, obj.content)
            continue
        raise GgraParserError(
            "Parser: Parsing modifiers of a pattern",
            ["Changes (with) or Condition (if) expected, ", f"got type {obj.__class__.__name__!r}"]
        )
    return current

def parse_nt_context(context_structures: list[Line]):
    opener, *content = context_structures
    patterns = [parse_group(group) for group in group_pattern_def(content)]
    return NtDefinition(
        opener.name,
        opener.param_names,
        patterns[0] if len(patterns) == 1 else PatternFrom(patterns)
    )

def parse_from_context(context_structures: list[Line]):
    _, *content = context_structures
    patterns = [parse_group(group) for group in group_pattern_def(content)]
    return PatternFrom(patterns)

def parse_with_context(context_structures: list[LineChange]):
    for obj in context_structures[1:]:
        if not isinstance(obj, LineChange):
            raise GgraParserError(
                "Parser: Parsing changes (lines in 'with')",
                ["Expected Change", f"got type {obj.__class__.__name__!r}"]
            )
    return With([structure.content for structure in context_structures[1:]])

#-----------------------
def parse_context(context_structures: list[Line]):
    opener = context_structures[0]
    if isinstance(opener, LineOpenNt):
        return parse_nt_context(context_structures)
    if isinstance(opener, LineOpenFrom):
        return parse_from_context(context_structures)
    if isinstance(opener, LineOpenWith):
        return parse_with_context(context_structures)
    raise GgraParserError(
        "Parser: Parsing indented contexts",
        ["Opener like nonterminal name, 'from' or 'with' expected", f"got {opener!r} of type {opener.__class__.__name__!r}"]
    )

#-----------------------
@time_info("Parsing the file")
def parse_file(file: TextIO) -> list[Nt]:
    return parse_file_from_lines(make_lines(line_iterator(file.read())))

def parse_file_from_lines(parsed_lines: Iterator[Line]) -> list[Nt]:
    contexts = [
        [0, []]
    ] # List of indents and structures on that level

    for line in parsed_lines:
        indent_here, structures = contexts[-1]
        indent = line.indent

        if indent_here is None:
            if indent == contexts[-2][0]:
                raise GgraParserError(
                    "Parser: Parsing file from indented contexts",
                    ["Content of a context needs to be indented:", f"(opener ind ({indent}) = context ind({indent}))"]
                )
            contexts[-1][0] = indent
            handle_line_context(contexts, line)
            continue
        
        if indent > indent_here:
            raise GgraParserError(
                "Parser: Parsing file from indented contexts",
                ["Wrong indent for line:", str(line), f"(expected ind: {indent_here}, got {indent})"]
            )
        if indent < indent_here:
            # If indents are closed
            while indent < indent_here:
                parsed_context = parse_context(structures)
                contexts.pop()
                indent_here, structures = contexts[-1]
                structures.append(parsed_context)
            if indent != indent_here:
                # If indent does not fit any indent level
                raise GgraParserError(
                    "Parser: Parsing file from indented contexts",
                    ["Wrong indent for line:", str(line), f"(expected ind: {indent_here}, got {indent})"]
                )
        
        handle_line_context(contexts, line)
    
    # Closing of contexts
    indent_here, structures = contexts[-1]
    while indent_here > 0:
        parsed_context = parse_context(structures)
        contexts.pop()
        indent_here, structures = contexts[-1]
        structures.append(parsed_context)
        
    return standardize_nts(contexts[0][1])

def standardize_nts(nt_defs: list[NtDefinition|LineFullNt|LineFileNt]) -> list[Nt]:
    """so that LineFullNt lines  also are converted to Nts"""
    definitions = []
    for definition in nt_defs:
        if isinstance(definition, NtDefinition):
            definitions.append(definition)
            continue
        if isinstance(definition, (LineFullNt, LineFileNt)):
            definitions.append(definition.to_nt())
            continue
        raise GgraParserError(
            "Parser: Creating nonterminal definitions",
            ["Expected nonterminal definition or nonterminal from file", f"got type {definition.__class__.__name__!r}"]
        )
    return definitions

