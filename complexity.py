import compiler
from compiler.visitor import ASTVisitor


class Complexity(ASTVisitor):
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
                                 type_='module',
                                 score=self.score,
                                 start_line=1,
                                 end_line=end_line))

    def dispatchChildren(self, node):
        for child in node.getChildNodes():
            self.dispatch(child)

    def visitFunction(self, node):
        score=Complexity(node).score
        stats = Stats(name=node.name,
                      type_='function',
                      score=score,
                      start_line=node.lineno,
                      end_line=self.highest_line_in_node(node))
        self.stats.add(stats)

    def visitClass(self, node):
        complexity = Complexity(node)
        self.stats.add(Stats(name=node.name,
                             type_='class',
                             score=complexity.score,
                             start_line=node.lineno,
                             end_line=self.highest_line_in_node(node)))
        for stats_instance in complexity.stats.ordered_by_line():
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

    def ordered_by_line(self):
        OBJECT_SORT_PRIORITY = ['module', 'function', 'class']
        def sort_key(stats):
            return (stats.start_line,
                    OBJECT_SORT_PRIORITY.index(stats.type_))
        return sorted(self._stats, key=sort_key)

    def named(self, name):
        return [s for s in self._stats if s.name == name][0]


class Stats:
    def __init__(self, name, type_, score, start_line, end_line):
        self.name = name
        self.type_ = type_
        self.score = score
        self.start_line = start_line
        self.end_line = end_line

    def __repr__(self):
        return 'Stats(name=%s, score=%s, start_line=%s, end_line=%s)' % (
            repr(self.name),
            repr(self.score),
            repr(self.start_line),
            repr(self.end_line))


def complexity_name(complexity):
    if complexity > 14:
        return 'high_complexity'
    elif complexity > 7:
        return 'medium_complexity'
    else:
        return 'low_complexity'


def show_complexity():
    try:
        current_file = get_current_file_name()
    except (IndentationError, SyntaxError):
        return

    stats = compute_stats_for_(current_file)
    old_complexities = get_old_complexities(current_file)
    new_complexities = compute_new_complexities(stats)
    line_changes = compute_line_changes(old_complexities, new_complexities)
    update_line_markers(line_changes)


def get_current_file_name():
    return vim.eval('expand("%:p")')


def compute_stats_for_(filename):
    code = open(filename).read()
    stats = Complexity(code).stats.ordered_by_line()
    return stats


def get_old_complexities(current_file):
    lines = list_current_signs(current_file)

    old_complexities = {}
    for line in lines:
        if '=' not in line:
            continue

        tokens = line.split()
        variables = dict(token.split('=') for token in tokens)
        line = int(variables['line'])
        complexity = variables['name']
        old_complexities[line] = complexity

    return old_complexities


def list_current_signs(current_file):
    vim.command('redir => s:complexity_sign_list')
    vim.command('silent sign place file=%s' % current_file)
    vim.command('redir END')

    sign_list = vim.eval('s:complexity_sign_list')
    lines = [line.strip() for line in sign_list.split('\n')]
    return lines


def compute_line_changes(cached_complexities, new_scores):
    changes = {}
    for line, complexity in new_scores.iteritems():
        if complexity != cached_complexities.get(line, None):
            changes[line] = complexity

    return changes


def compute_new_complexities(stats):
    new_scores = {}
    for stat in stats:
        for line in range(stat.start_line, stat.end_line + 1):
            new_scores[line] = complexity_name(stat.score)
    return new_scores


def update_line_markers(line_changes):
    for line, complexity in line_changes.iteritems():
        vim.command(':sign place %i line=%i name=%s file=%s' %
                    (line, line, complexity, vim.eval('expand("%:p")')))

