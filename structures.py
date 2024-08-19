
from abc import ABC
from dataclasses import dataclass
import json
from os import path
from random import choice#, shuffle # Achtung! Inplace
from typing import Iterator, Self

from .change_graph import Graph
from .helpers import shuffle, first_where, separate, time_info


#=================================
# CONDITIONS
class Condition(ABC):
    """Conditions may also be Expressions"""
    def evaluate(self, params: dict[str, str]):
        pass

class Expression(Condition):
    pass

@dataclass
class ExpressionIdentifier(Expression):
    name: str
    def evaluate(self, params) -> str:
        if self.name not in params:
            raise Exception(f"Identifier evaluation # identifier {self.name!r} unknown!")
        return params[self.name]

@dataclass
class ExpressionString(Expression):
    content: str
    def evaluate(self, params) -> str:
        return self.content

@dataclass
class ExpressionChoice(Expression):
    options: list[Expression]
    def evaluate(self, params) -> Iterator:
        return (op.evaluate(params) for op in self.options)

@dataclass
class ConditionEq(Condition):
    first: Condition | Expression
    second: Condition | Expression
    def evaluate(self, params) -> bool:
        # f = self.first.evaluate(params)
        # s = self.second.evaluate(params)
        # return f == s
        options = lambda part: part.evaluate(params) if isinstance(part, ExpressionChoice) else [part.evaluate(params)]

        for opt_f in options(self.first):
            for opt_s in options(self.second):
                if opt_f == opt_s:
                    return True
        return False
        
@dataclass
class ConditionNeq(Condition):
    first: Condition | Expression
    second: Condition | Expression
    def evaluate(self, params) -> bool:
        options = lambda part: part.evaluate(params) if isinstance(part, ExpressionChoice) else [part.evaluate(params)]

        for opt_f in options(self.first):
            for opt_s in options(self.second):
                if opt_f != opt_s:
                    return True
        return False

#=================================
# CHANGE, WITH
class Source(ABC):
    pass

@dataclass
class SourceNonterminal(Source):
    nt_name: str
    nt_param: str

@dataclass
class SourceString(Source):
    content: str

@dataclass
class SourceIdentifier(Source):
    name: str

@dataclass
class SourceChoice(Source):
    options: list[Source]
    def choose_one(self):
        return choice(self.options)

@dataclass
class Change:
    source: Source
    target_nt_name: str
    target_nt_param: str

    def decided_source(self):
        """resolves SourceChoice to one of the choices\n
        in cases like `"a"|name`"""
        if isinstance(self.source, SourceChoice):
            return self.source.choose_one()
        return self.source

@dataclass
class With:
    changes: list[Change]

#=================================
# PATTERNS
class Pattern(ABC):
    def resolve(self, params: dict[str, str]) -> tuple[list, list[Change]]:
        pass

#-----------------------
class Element(ABC):
    def resolve(self):
        pass

@dataclass
class ElementNonterminal(Element):
    name: str
    def resolve(self):
        return self

@dataclass
class ElementString(Element):
    content: str
    def resolve(self):
        return self.content
@dataclass
class PatternBNForm(Pattern):
    elements: list[Element]
    def resolve(self, params):
        return [element.resolve() for element in self.elements], []

#-----------------------
@dataclass
class PatternFrom(Pattern):
    subpatterns: list[Pattern]
    def resolve(self, params):
        subs = self.subpatterns.copy()
        subs = shuffle(subs)
        subs_resolved = (sub.resolve(params) for sub in subs)
        sub_with_result = first_where(
            subs_resolved,
            lambda sub: sub[0] is not None,
            (None, None)
        )
        return sub_with_result
        
@dataclass
class PatternIf(Pattern):
    subpattern: Pattern
    condition: Condition
    def resolve(self, params):
        if not self.condition.evaluate(params):
            return None, None
        return self.subpattern.resolve(params)

@dataclass
class PatternWith(Pattern):
    subpattern: Pattern
    changes: With
    def resolve(self, params):
        sub, changes = self.subpattern.resolve(params)
        res = sub, changes + self.changes.changes
        return res

#=================================
#NONTERMINAL DEFINITION
@dataclass
class Nt(ABC):
    name: str
    param_names: set[str]
    def resolve(self, nt_definitions: list[Self], params: dict[str, str]) -> list[str]:
        pass

@dataclass
class NtFile(Nt):
    filename: str
    json_content = None

    # @time_info("Loading JSON")
    def load_json_content(self):
        if not path.exists(self.filename):
            raise Exception(f"File {self.filename!r} does not exist! (for resolution of Nonterminal {self.name!r} from file)")
        with open(self.filename, "r", encoding="utf-8") as doc:
            self.json_content = json.load(doc)
    
    def query(self, query: list[str]) -> str | list[str] | None:
        field = self.json_content.get("content")
        for specifier in query:
            if specifier == "...":
                field = choice(field)
            else:
                field = field.get(specifier, None)
            if field is None:
                return None
        return field

    def resolve(self, nt_definitions, params: dict[str, str]) -> list[str]:
        if self.json_content is None:
            self.load_json_content()
        
        order:list = self.json_content.get("order")

        order_nochoose = [elem for elem in order if elem != "..."]

        if set(order_nochoose) != set(params):
            raise Exception(f"NtFile.resolve # parameters {set(params)} for NtFile {self.name!r} do not fit parameters in file ({set(order_nochoose)})")
        
        # "..." corresponds to a choice using "from" in the json files
        query = [specifier if specifier == "..." else params.get(specifier) for specifier in order] 
        result = self.query(query)

        if result is None:
            raise Exception(f"NtFile.resolve # no result for params {params!r} in Nonterminal from file {self.name!r}")
        if isinstance(result, str):
            return [result]
        return result


@dataclass
class NtDefinition(Nt):
    subpattern: Pattern

    def resolve(self, nt_definitions, params: dict[str, str]) -> list[str]:
        pattern, changes = self.subpattern.resolve(params)

        if pattern is None:
            raise Exception(f"NtDefinition.resolve # unresolvable subpattern for Nonterminal {self.name!r}")

        nts = set (elem.name.removeprefix("~") for elem in pattern if isinstance(elem, ElementNonterminal))
        
        nt_changes, constant_changes = separate(changes, lambda change: isinstance(change.source, SourceNonterminal))
        
        nt_config = {nt_name : dict() for nt_name in nts}
        # Execution of changes
        execute_constants(constant_changes, nt_config, params)
        sorted_changes = sort_changes(nt_changes)
        for change in sorted_changes:
            execute_change(change, nt_config)
        
        # for change in changes:
        #     change.restore()
        
        return fill_in_pattern(pattern, nt_config, nt_definitions)

#-----------------------
def error_check_change_id(change: Change, params: dict[str, str]):
    if change.source.name not in params:
        raise Exception(f"NtDefinition.resolve # Parameter {change.source.name!r} does not exist.")

def fits_nt_def_params(nt_definition: Nt, params: set[str]) -> bool:
    return nt_definition.param_names == params

def resolve_nt(nt_definitions: list[Nt], nt_name: str, params: dict[str, str]) -> list[str]:
    param_set = set(key for key in params)
    shuffled_defs = nt_definitions.copy()
    shuffled_defs = shuffle(shuffled_defs)
    definition = first_where(
        shuffled_defs,
        lambda nt_definition: nt_definition.name == nt_name and fits_nt_def_params(nt_definition, param_set)
    )
    if definition is None:
        param_names = ", ".join(sorted(list(param_set)))
        raise Exception(f"resolve_nt # There exists no Nonterminal Definition that fits {nt_name}({param_names}).")
    return definition.resolve(nt_definitions, params)

def sort_changes(nt_changes: list[Change]) -> list[Change]:
    nt_graph    = Graph()
    for change in nt_changes:
        nt_graph.add_edge(change.source.nt_name, change.target_nt_name)
    # Topological sorting of the change graph
    nt_priorities   = nt_graph.topological_sort()
    sorted_changes  = sorted(nt_changes, key=lambda change: nt_priorities.index(change.source.nt_name))
    return sorted_changes

def execute_constants(constant_changes: list[Change], nt_configuration: dict[str, dict], params: dict[str, str]):
    for change in constant_changes:
        source      = change.decided_source()
        target_name = change.target_nt_name
        target_param = change.target_nt_param
        
        if change.target_nt_name not in nt_configuration:
            raise Exception(f"NtDefinition.resolve # Nonterminal {change.target_nt_name} does not exist.")
        if isinstance(source, SourceIdentifier):
            error_check_change_id(change, params)
            nt_configuration[target_name][target_param] = params[source.name]
            continue
        if isinstance(source, SourceString):
            nt_configuration[target_name][target_param] = source.content
            continue
        # raise Exception(f"! Strange type {source}")

def execute_change(change: Change, nt_configuration: dict[str, dict[str, str]]):
    """Implements a change in the configuration for Nonterminals"""
    source_name = change.source.nt_name
    source_param = change.source.nt_param
    target_name = change.target_nt_name
    target_param = change.target_nt_param
    nt_configuration[target_name][target_param] = nt_configuration[source_name][source_param]

def resolve_pattern_nt(
        nt_name: str,
        nts_resolved: dict[str, list[str]],
        nt_configuration: dict[str, dict[str, str]],
        nt_definitions: list[Nt]
    ) -> list[str]:
    if nt_name.startswith("~"):
        # separately resolve the Nonterminal
        actual_name = nt_name.removeprefix("~")
        return resolve_nt(nt_definitions, actual_name, nt_configuration[actual_name])
    if nt_name not in nts_resolved:
        raise Exception(f"fill_in_pattern # Nonterminal {nt_name!r} in pattern not resolved!")
    if nts_resolved[nt_name] is None:
        # nt gets resolved just when needed.
        # This way, rules regarding nonexistent nts dont do anything
        # Also, performance might be improved
        nts_resolved[nt_name] = resolve_nt(nt_definitions, nt_name, nt_configuration[nt_name])
    return nts_resolved[nt_name]

def fill_in_pattern(pattern: list[str | ElementNonterminal], nt_configuration: dict[str, dict[str, str]], nt_definitions: list[Nt]) -> list[str]:
    """Makes a list of resolved contents out of the pattern and its config"""
    nts_resolved = {nt_name : None for nt_name in nt_configuration}
    p = []
    for obj in pattern:
        if isinstance(obj, str):
            p.append(obj)
        else:
            res = resolve_pattern_nt(obj.name, nts_resolved, nt_configuration, nt_definitions)
            p.extend(res)
    return p
