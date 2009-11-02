" complexity.vim
" Gary Bernhardt (http://blog.extracheese.org)
"
" This will add cyclomatic complexity annotations to your source code. It is
" no longer wrong (as previous versions were!) However, it is now much slower.
" Almost all of the time is spent setting up the signs in vim, which clearly
" wasn't meant to track this many signs at once. I'd like to speed this up by
" having the Python code remember where it placed the signs, and only change
" them if they actually changed in the code. Contributions are welcome!

python << endpython
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
                                 score=self.score,
                                 start_line=1,
                                 end_line=end_line))

    def dispatchChildren(self, node):
        for child in node.getChildNodes():
            self.dispatch(child)

    def visitFunction(self, node):
        score=Complexity(node).score
        stats = Stats(name=node.name,
                      score=score,
                      start_line=node.lineno,
                      end_line=self.highest_line_in_node(node))
        self.stats.add(stats)

    def visitClass(self, node):
        complexity = Complexity(node)
        self.stats.add(Stats(name=node.name,
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
        return sorted(self._stats, key=lambda stats: stats.start_line)

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
        stats = Complexity(code).stats.ordered_by_line()
    except (IndentationError, SyntaxError):
        return

    vim.command('sign unplace *')

    for stat in stats:
        complexity = complexity_name(stat.score)
        for line in range(stat.start_line, stat.end_line + 1):
            vim.command(':sign place %i line=%i name=%s file=%s' %
                        (line, line, complexity, vim.eval('expand("%:p")')))


endpython

function! ShowComplexity()
    python << END
show_complexity()
END
endfunction

hi SignColumn guifg=fg guibg=bg
hi low_complexity guifg=#004400 guibg=#004400
hi medium_complexity guifg=#bbbb00 guibg=#bbbb00
hi high_complexity guifg=#ff2222 guibg=#ff2222
sign define low_complexity text=XX texthl=low_complexity
sign define medium_complexity text=XX texthl=medium_complexity
sign define high_complexity text=XX texthl=high_complexity

autocmd! BufReadPost,BufWritePost,FileReadPost,FileWritePost *.py call ShowComplexity()

