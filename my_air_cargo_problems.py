from aimacode.logic import PropKB
from aimacode.planning import Action
from aimacode.search import (
    Node, Problem,
)
from aimacode.utils import expr
from lp_utils import (
    FluentState, encode_state, decode_state,
)
from my_planning_graph import PlanningGraph

from functools import lru_cache


class AirCargoProblem(Problem):
    def __init__(self, cargos, planes, airports, initial: FluentState, goal: list):
        """

        :param cargos: list of str
            cargos in the problem
        :param planes: list of str
            planes in the problem
        :param airports: list of str
            airports in the problem
        :param initial: FluentState object
            positive and negative literal fluents (as expr) describing initial state
        :param goal: list of expr
            literal fluents required for goal test
        """
        self.state_map = initial.pos + initial.neg
        self.initial_state_TF = encode_state(initial, self.state_map)
        Problem.__init__(self, self.initial_state_TF, goal=goal)
        self.cargos = cargos
        self.planes = planes
        self.airports = airports
        self.actions_list = self.get_actions()

    def get_actions(self):
        """
        This method creates concrete actions (no variables) for all actions in the problem
        domain action schema and turns them into complete Action objects as defined in the
        aimacode.planning module. It is computationally expensive to call this method directly;
        however, it is called in the constructor and the results cached in the `actions_list` property.

        Returns:
        ----------
        list<Action>
            list of Action objects
        """

        # TODO create concrete Action objects based on the domain action schema for: Load, Unload, and Fly
        # concrete actions definition: specific literal action that does not include variables as with the schema
        # for example, the action schema 'Load(c, p, a)' can represent the concrete actions 'Load(C1, P1, SFO)'
        # or 'Load(C2, P2, JFK)'.  The actions for the planning problem must be concrete because the problems in
        # forward search and Planning Graphs must use Propositional Logic

        def load_actions():
            """Create all concrete Load actions and return a list

            :return: list of Action objects
            """
            loads = []
            # TODO comment this snippet
            for airport in self.airports:
                for cargo in self.cargos:
                    for plane in self.planes:
                        positive_preconditions = [expr("At({}, {})".format(plane, airport)),
                                                  expr("At({}, {})".format(cargo, airport))]
                        negative_preconditions = []
                        positive_effect = [expr("In({}, {})".format(cargo, plane))]
                        negative_effect = [expr("At({}, {})".format(cargo, airport))]

                        load = Action(expr("Load({}, {}, {})".format(cargo, plane, airport)),
                                      [positive_preconditions, negative_preconditions],
                                      [positive_effect, negative_effect])

                        loads.append(load)

            return loads

        def unload_actions():
            """Create all concrete Unload actions and return a list

            :return: list of Action objects
            """
            # TODO comment this snippet
            unloads = []
            for airport in self.airports:
                for cargo in self.cargos:
                    for plane in self.planes:
                        positive_preconditions = [expr("In({}, {})".format(cargo, plane)),
                                                  expr("At({}, {})".format(plane, airport))]
                        negative_preconditions = []
                        positive_effect = [expr("At({}, {})".format(cargo, airport))]
                        negative_effect = [expr("In({}, {})".format(cargo, plane))]

                        unload = Action(expr("Unload({}, {}, {})".format(cargo, plane, airport)),
                                      [positive_preconditions, negative_preconditions],
                                      [positive_effect, negative_effect])

                        unloads.append(unload)

            return unloads

        def fly_actions():
            """Create all concrete Fly actions and return a list

            :return: list of Action objects
            """
            # TODO comment this snippet
            flys = []
            for fr in self.airports:
                for to in self.airports:
                    if fr != to:
                        for p in self.planes:
                            precond_pos = [expr("At({}, {})".format(p, fr)),
                                           ]
                            precond_neg = []
                            effect_add = [expr("At({}, {})".format(p, to))]
                            effect_rem = [expr("At({}, {})".format(p, fr))]
                            fly = Action(expr("Fly({}, {}, {})".format(p, fr, to)),
                                         [precond_pos, precond_neg],
                                         [effect_add, effect_rem])
                            flys.append(fly)
            return flys

        return load_actions() + unload_actions() + fly_actions()

    def actions(self, state: str) -> list:
        """ Return the actions that can be executed in the given state.

        :param state: str
            state represented as T/F string of mapped fluents (state variables)
            e.g. 'FTTTFF'
        :return: list of Action objects
        """

        possible_actions = []

        # Get all the possible actions without checking if they can be executed
        actions = self.get_actions()

        # Decode the state, to get an object with separate positive and negative fluents
        fluent_state = decode_state(state, self.state_map)

        for action in actions:
            can = True
            # Check all the positive preconditions of the action are satisfied
            for pre_pos in action.precond_pos:
                if pre_pos not in fluent_state.pos:
                    can = False

            # Check all the negative preconditions of the action are satisfied
            for pre_neg in action.precond_neg:
                if pre_neg not in fluent_state.neg:
                    can = False

            # If all the preconditions are satisfied, append the action to the possible actions
            if can:
                possible_actions.append(action)

        return possible_actions

    def result(self, state: str, action: Action):
        """ Return the state that results from executing the given
        action in the given state. The action must be one of
        self.actions(state).

        :param state: state entering node
        :param action: Action applied
        :return: resulting state after action
        """

        new_state = list(state)

        for add_eff in action.effect_add:
            position = self.state_map.index(add_eff)
            new_state[position] = 'T'
        for rem_eff in action.effect_rem:
            position = self.state_map.index(rem_eff)
            new_state[position] = 'F'

        return "".join(new_state)

    def goal_test(self, state: str) -> bool:
        """ Test the state to see if goal is reached

        :param state: str representing state
        :return: bool
        """
        kb = PropKB()
        kb.tell(decode_state(state, self.state_map).pos_sentence())
        for clause in self.goal:
            if clause not in kb.clauses:
                return False
        return True

    def h_1(self, node: Node):
        # note that this is not a true heuristic
        h_const = 1
        return h_const

    @lru_cache(maxsize=8192)
    def h_pg_levelsum(self, node: Node):
        """This heuristic uses a planning graph representation of the problem
        state space to estimate the sum of all actions that must be carried
        out from the current state in order to satisfy each individual goal
        condition.
        """
        # requires implemented PlanningGraph class
        pg = PlanningGraph(self, node.state)
        pg_levelsum = pg.h_levelsum()
        return pg_levelsum

    @lru_cache(maxsize=8192)
    def h_ignore_preconditions(self, node: Node):
        """This heuristic estimates the minimum number of actions that must be
        carried out from the current state in order to satisfy all of the goal
        conditions by ignoring the preconditions required for an action to be
        executed.
        """
        # TODO implement (see Russell-Norvig Ed-3 10.2.3  or Russell-Norvig Ed-2 11.2)
        count = 0
        return count


def air_cargo_p1() -> AirCargoProblem:
    cargos = ['C1', 'C2']
    planes = ['P1', 'P2']
    airports = ['JFK', 'SFO']
    pos = [expr('At(C1, SFO)'),
           expr('At(C2, JFK)'),
           expr('At(P1, SFO)'),
           expr('At(P2, JFK)'),
           ]
    neg = [expr('At(C2, SFO)'),
           expr('In(C2, P1)'),
           expr('In(C2, P2)'),
           expr('At(C1, JFK)'),
           expr('In(C1, P1)'),
           expr('In(C1, P2)'),
           expr('At(P1, JFK)'),
           expr('At(P2, SFO)'),
           ]
    init = FluentState(pos, neg)
    goal = [expr('At(C1, JFK)'),
            expr('At(C2, SFO)'),
            ]
    return AirCargoProblem(cargos, planes, airports, init, goal)


# # TODO: Ver cómo son los objetos con el debugueador
# problem = air_cargo_p1()
# actions = problem.actions_list
# problem.result(problem.initial_state_TF, actions[4])


def air_cargo_p2() -> AirCargoProblem:
    # TODO implement Problem 2 definition
    pass


def air_cargo_p3() -> AirCargoProblem:
    # TODO implement Problem 3 definition
    pass


pass
