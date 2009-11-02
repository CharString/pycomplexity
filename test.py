from textwrap import dedent

from complexity import Complexity


class describe_simple_statements:
    def test_pass(self):
        assert complexity('pass') == 1

    def test_statement_sequence(self):
        assert complexity(
            """
            pass
            pass
            """) == 1

    def test_constant(self):
        assert complexity("1") == 1

    def test_assignment(self):
        assert complexity("x = 1") == 1

    def test_name(self):
        assert complexity("a") == 1

    def test_sequence_of_names(self):
        assert complexity(
            """
            a
            b
            c
            """) == 1


class describe_conditionals:
    def test_simple_branch(self):
        assert complexity(
            """
            if x: 1
            # implicit else
            """) == 2

    def test_branch_with_else(self):
        assert complexity(
            """
            if x: 1
            else: 2
            """) == 2

    def test_branch_with_else_if(self):
        assert complexity(
            """
            if x: 1
            elif y: 2
            # implicit else
            """) == 3

    def test_branch_with_else_if_and_else(self):
        assert complexity(
            """
            if x: 1
            elif y: 2
            else: 3
            """) == 3

    def test_child_nodes_of_ifs(self):
        assert complexity(
            """
            if x:
                if y: 1
                else: 2
            else: 3
            """) == 3

    def test_child_nodes_of_elses(self):
        assert complexity(
            """
            if x: 1
            else:
                if y: 1
                # implicit else
            """) == 3


class describe_inline_conditionals:
    def test_inline_conditionals(self):
        assert complexity("b if c else d") == 2

    def test_nested_inline_conditionals(self):
        assert complexity(
            """
            (b
             if c
             else (d
                   if e
                   else f))
            """) == 3


class describe_for_loops:
    def test_for_loops(self):
        assert complexity(
            """
            for x in y: 1
            # implicit else
            """) == 2

    def test_else_clauses_on_for_loops(self):
        assert complexity(
            """
            for x in y: 1
            else: 2
            """) == 2

    def test_child_nodes_of_for_loops(self):
        assert complexity(
            """
            for x in y:
                if x: 1
                else: 2
            # implicit else
            """) == 3

    def test_child_nodes_in_for_loop_else_clauses(self):
        assert complexity(
            """
            for x in y: 1
            else:
                if x: 2
                else: 3
            """) == 3

    def test_break_statements_in_for_loops(self):
        # This seems like it should be more complex than an if with "pass"es,
        # but it's not. The break just reroutes the "if" path: instead of
        # going to the end of the loop and back up top, it goes straight back
        # up.
        assert complexity(
            """
            for x in y:
                if x:
                    break
            """) == 3

    def test_break_statements_in_for_loops_with_else_clauses(self):
        # A "break" in a for loop skips the "else". My intuitive
        # interpretation is that this should increase CC by one. However, it's
        # basically a GOTO, and GOTOs don't increase the CC. Drawing the graph
        # out seems to confirm that a "break" with an "else" does not add a
        # path.
        assert complexity(
            """
            for x in y:
                if x:
                    break
            else:
                pass
            """) == 3


# These are basically identical to the "for" loop tests, but abstracting them
# to remove the duplication would be just as long and more confusing.
class describe_while_loops:
    def test_while_loops(self):
        assert complexity(
            """
            while x: 1
            # implicit else
            """) == 2

    def test_else_clauses_on_while_loops(self):
        assert complexity(
            """
            while x: 1
            else: 2
            """) == 2

    def test_child_nodes_of_while_loops(self):
        assert complexity(
            """
            while x:
                if x: 1
                else: 2
            # implicit else
            """) == 3

    def test_child_nodes_in_while_loop_else_clauses(self):
        assert complexity(
            """
            while x: 1
            else:
                if x: 2
                else: 3
            """) == 3

    def test_break_statements_in_while_loops(self):
        # See discussion for "for" loops above.
        assert complexity(
            """
            while x:
                if x:
                    break
            """) == 3

    def test_break_statements_in_while_loops_with_else_clauses(self):
        # See discussion for for loops above.
        assert complexity(
            """
            while x:
                if x:
                    break
            else:
                pass
            """) == 3


class describe_integration:
    def test_multiple_ifs_in_a_for_loop(self):
        assert complexity(
            """
            for x in y:
                if x: pass
                # implicit else
                if y: pass
                # implicit else
            """) == 5


#test_compound_conditionals
#test_continue_statements_in_for_loops


def complexity(code):
    return Complexity(dedent(code)).score

