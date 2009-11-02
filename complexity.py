import compiler
from compiler.visitor import ASTVisitor


class Complexity(ASTVisitor):
    """Encapsulates the cyclomatic complexity counting."""

    def __init__(self, code_or_node, stats=None, description=None):
        ASTVisitor.__init__(self)
        try:
            node = compiler.parse(code_or_node)
        except TypeError:
            node = code_or_node
            in_module = False
        else:
            in_module = True

        self.score = 1
        self._in_conditional = False
        self.stats = StatsCollection()
        for child in node.getChildNodes():
            compiler.walk(child, self, walker=self)

        if in_module:
            end_line = max(1, code_or_node.count('\n') + 1)
            self.stats.add(Stats(name='<module>',
                                 score=self.score,
                                 start_line=1,
                                 end_line=end_line))

    def dispatchChildren(self, node):
        for child in node.getChildNodes():
            self.dispatch(child)

    def visitFunction(self, node):
        #if not hasattr(node, 'name'): # lambdas
        #    node.name = '<lambda>'
        score=Complexity(node).score
        stats = Stats(name=node.name,
                      score=score,
                      start_line=node.lineno,
                      end_line=self.highest_line_in_node(node))
        self.stats.add(stats)

    #visitLambda = visitFunction

    def visitClass(self, node):
        complexity = Complexity(node)
        self.stats.add(Stats(name=node.name,
                             score=complexity.score,
                             start_line=node.lineno,
                             end_line=self.highest_line_in_node(node)))
        for stats_instance in complexity.stats.all():
            stats_instance.name = '%s.%s' % (node.name, stats_instance.name)
            self.stats.add(stats_instance)

    def highest_line_in_node(self, node, highest=0):
        children = node.getChildNodes()
        if node.lineno > highest:
            highest = node.lineno
        child_lines = map(self.highest_line_in_node,
                          node.getChildNodes())
        lines = [node.lineno] + child_lines
        return max(lines)

    def visitIf(self, node):
        tests = self._tests_for_if(node)
        self.score += len(tests)
        self._in_conditional = True
        for test in tests:
            self.dispatch(test)
        self._in_conditional = False
        self.dispatchChildren(node)

    def _tests_for_if(self, if_node):
        try:
            return [test for test, body in if_node.tests]
        except AttributeError:
            return [if_node.test]

    visitGenExprIf = visitListCompIf = visitIfExp = visitIf

    def __processDecisionPoint(self, node):
        self.score += 1
        self.dispatchChildren(node)

    visitFor = visitGenExprFor \
            = visitListCompFor \
            = visitWhile = __processDecisionPoint

    def _visit_logical_operator(self, node):
        self.dispatchChildren(node)
        if self._in_conditional:
            self.score += len(node.getChildren()) - 1

    visitAnd = _visit_logical_operator
    visitOr = _visit_logical_operator

    def visitTryExcept(self, node):
        self.dispatchChildren(node)
        self.score += len(node.handlers)


class StatsCollection:
    def __init__(self):
        self._stats = []

    def add(self, stats):
        self._stats.append(stats)

    def all(self):
        return self._stats[:]

    def named(self, name):
        return [s for s in self._stats if s.name == name][0]


class Stats:
    def __init__(self, name, score, start_line, end_line):
        self.name = name
        self.score = score
        self.start_line = start_line
        self.end_line = end_line

    def __repr__(self):
        return 'Stats(name=%s, score=%s, start_line=%s, end_line=%s)' % (
            repr(self.name),
            repr(self.score),
            repr(self.start_line),
            repr(self.end_line))


def measure_complexity(ast, module_name=None):
    return CCVisitor(ast, description=module_name).stats


class PrettyPrinter(object):
    def flatten_stats(self, stats):
        def flatten(stats):
            for s in stats.classes:
                name = s.name
                for x in s.functions:
                    fname = '.'.join([name, x.name])
                    yield fname, x.complexity, x.first_line, x.last_line
            for s in stats.functions:
                name = s.name
                yield name, s.complexity, s.first_line, s.last_line

        return [t for t in flatten(stats)]


def complexity_name(complexity):
    if complexity > 14:
        return 'high_complexity'
    elif complexity > 7:
        return 'medium_complexity'
    else:
        return 'low_complexity'


def show_complexity():
    import vim

    current_file = vim.eval('expand("%:p")')
    code = open(current_file).read()
    try:
        stats = Complexity(code).stats
    except (IndentationError, SyntaxError):
        return

    vim.command('sign unplace *')

    for stat in stats:
        complexity = complexity_name(stat.score)
        for line in range(stat.start_line, stat.end_line + 1):
            vim.command(':sign place %i line=%i name=%s file=%s' %
                        (line, line, complexity, vim.eval('expand("%:p")')))

