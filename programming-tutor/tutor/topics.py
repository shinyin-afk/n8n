"""Topic classification and per-topic teaching content.

This module is the tutor's "subject matter" brain.  Each :class:`Topic`
carries enough content to build a hint at every rung of the hint ladder,
plus a ``complexity`` score (0..1) that the capability profiler uses as a
signal of how hard the learner's work is.

The classifier is intentionally simple (keyword matching) so the whole
prototype stays deterministic and testable with no model behind it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Topic:
    """One teachable subject and the content needed to hint at it."""

    key: str
    label: str
    complexity: float
    keywords: List[str]
    concept_question: str          # ladder rung 1
    plan_steps: List[str]          # ladder rung 2
    analogy: str                   # ladder rung 3 (related but different problem)
    skeleton: str                  # ladder rung 4 (near-solution with a gap)


TOPICS: List[Topic] = [
    Topic(
        key="loops",
        label="loops and iteration",
        complexity=0.25,
        keywords=["loop", "iterate", "iteration", "for each", "while"],
        concept_question=(
            "Think about what changes on each pass through the loop: "
            "what is the loop variable, and when should the loop stop?"
        ),
        plan_steps=[
            "Write down the list of things that must happen once per item.",
            "Choose the loop variable and its starting value.",
            "Decide the stop condition (what makes the loop end).",
            "State what the loop should update on each pass.",
        ],
        analogy=(
            "A related idea: summing the numbers 1 to 10 with a loop.  "
            "Keep a running total, start it at 0, and add each number in "
            "turn.  Notice how the *running total* plays the role of the "
            "answer you are accumulating.  Your problem likely accumulates "
            "something too."
        ),
        skeleton=(
            "result = <initial value>\n"
            "for item in <collection>:\n"
            "    # TODO: update result using item\n"
        ),
    ),
    Topic(
        key="lists",
        label="lists and arrays",
        complexity=0.3,
        keywords=["list", "array", "index", "slice", "element", "append"],
        concept_question=(
            "Are you trying to read an element, change one, or build a new "
            "collection?  Which index or position does your answer depend on?"
        ),
        plan_steps=[
            "Clarify whether you mutate the list in place or build a new one.",
            "Identify the position(s) you need to touch.",
            "Handle the edge: what happens when the list is empty?",
            "Verify your result against a tiny example by hand.",
        ],
        analogy=(
            "Related idea: reversing a list.  You can swap the first and "
            "last elements, then move inward.  The trick is tracking two "
            "positions at once.  Check whether your problem also needs two "
            "positions rather than one."
        ),
        skeleton=(
            "def solve(items):\n"
            "    out = []\n"
            "    for i, item in enumerate(items):\n"
            "        # TODO: decide what to keep or transform\n"
            "    return out\n"
        ),
    ),
    Topic(
        key="dicts",
        label="dictionaries and maps",
        complexity=0.35,
        keywords=["dict", "dictionary", "hashmap", "key-value", "lookup",
                  "associate"],
        concept_question=(
            "What is the *key* you look things up by, and what is the value "
            "you store under it?  Could you answer with a single lookup "
            "instead of a scan?"
        ),
        plan_steps=[
            "Decide the key and the value for your map.",
            "Pre-fill any counts or defaults before the main pass.",
            "Update the map as you go, keyed by what you identified.",
            "Read the final answer back out by its key.",
        ],
        analogy=(
            "Related idea: counting word frequencies.  For each word, add 1 "
            "to a map keyed by the word (using a default of 0).  After one "
            "pass the map holds every count.  Your problem likely wants the "
            "same 'key -> running value' pattern."
        ),
        skeleton=(
            "lookup = {}\n"
            "for x in <items>:\n"
            "    key = <derive key from x>\n"
            "    # TODO: update lookup[key]\n"
        ),
    ),
    Topic(
        key="recursion",
        label="recursion",
        complexity=0.7,
        keywords=["recursion", "recursive", "base case", "call itself"],
        concept_question=(
            "What is the smallest version of the problem you can answer "
            "without any recursion (the base case)?  And how does a bigger "
            "case shrink toward it?"
        ),
        plan_steps=[
            "Write the base case(s) first: the input where the answer is obvious.",
            "Express the general case in terms of a smaller instance of itself.",
            "Check that every recursive call makes real progress toward the base case.",
            "Trace one small example by hand to confirm it terminates.",
        ],
        analogy=(
            "Related idea: factorial.  factorial(0) is 1 (base case), and "
            "factorial(n) = n * factorial(n-1).  The key is that each call "
            "shrinks n toward 0.  Find the analogous shrink-step in your "
            "problem."
        ),
        skeleton=(
            "def solve(n):\n"
            "    if <base case>:\n"
            "        return <base value>\n"
            "    # TODO: return solve(smaller) combined with the current step\n"
        ),
    ),
    Topic(
        key="sorting",
        label="sorting",
        complexity=0.45,
        keywords=["sort", "sorted", "order", "ordering", "rank"],
        concept_question=(
            "What makes one item come before another?  Can you write that "
            "comparison as a single rule?"
        ),
        plan_steps=[
            "Define the ordering rule: how do two items compare?",
            "Pick the key (the field) you sort by, if any.",
            "Consider stability and duplicates: what should tie order be?",
            "Test with two items, then three, then a reversed list.",
        ],
        analogy=(
            "Related idea: sorting a deck of cards by hand.  You repeatedly "
            "pull the smallest card to the front.  The comparison 'is this "
            "card smaller?' is the whole heart of the matter.  Your problem "
            "boils down to defining that comparison."
        ),
        skeleton=(
            "def key(item):\n"
            "    # TODO: return the value to sort by\n"
            "result = sorted(items, key=key)\n"
        ),
    ),
    Topic(
        key="dynamic-programming",
        label="dynamic programming",
        complexity=0.9,
        keywords=["dynamic programming", "memoization", "memoize", "subproblem",
                  "fibonacci", "cache"],
        concept_question=(
            "Which subproblem's answer do you compute more than once?  Can you "
            "store that answer and reuse it instead of recomputing?"
        ),
        plan_steps=[
            "Name the subproblem and its parameters.",
            "Write the recurrence: how does a bigger answer combine smaller ones?",
            "Add a cache (memo) so each subproblem is solved once.",
            "Decide the order you fill answers in (or use recursion + cache).",
        ],
        analogy=(
            "Related idea: Fibonacci.  fib(n) = fib(n-1) + fib(n-2) recomputes "
            "fib(n-2) many times; caching each result makes it fast.  The "
            "tell-tale sign is the same subproblem reappearing.  Look for that "
            "repetition in your problem."
        ),
        skeleton=(
            "memo = {}\n"
            "def solve(state):\n"
            "    if state in memo:\n"
            "        return memo[state]\n"
            "    if <base case>:\n"
            "        return <base value>\n"
            "    # TODO: combine solve(smaller states) and store it\n"
        ),
    ),
    Topic(
        key="trees",
        label="trees and traversal",
        complexity=0.7,
        keywords=["tree", "binary tree", "root", "leaf", "traversal", "bst"],
        concept_question=(
            "At a single node, what do you need from its left subtree and its "
            "right subtree to produce the answer for this node?"
        ),
        plan_steps=[
            "Decide the traversal order (pre-, in-, post-order).",
            "Write what to do at an empty/null node first.",
            "Combine the child results at the current node.",
            "Trace a 3-node tree by hand.",
        ],
        analogy=(
            "Related idea: summing all values in a tree.  The sum at a node is "
            "its value plus the sums of its two children; a null node is 0.  "
            "The 'combine children' step is what you need to find in your "
            "problem."
        ),
        skeleton=(
            "def solve(node):\n"
            "    if node is None:\n"
            "        return <base value>\n"
            "    left = solve(node.left)\n"
            "    right = solve(node.right)\n"
            "    # TODO: combine node, left, right\n"
        ),
    ),
    Topic(
        key="graphs",
        label="graphs and search",
        complexity=0.8,
        keywords=["graph", "bfs", "dfs", "breadth", "depth", "adjacency",
                  "shortest path", "neighbor"],
        concept_question=(
            "What are the nodes and the edges in your problem?  Do you need "
            "shortest distance (breadth-first) or any path (depth-first)?"
        ),
        plan_steps=[
            "Model the state as a node and moves as edges.",
            "Choose BFS for shortest path, DFS for reachability.",
            "Track visited nodes to avoid infinite loops.",
            "Record how you reached each node to reconstruct the path.",
        ],
        analogy=(
            "Related idea: escaping a maze.  Each room is a node, each door an "
            "edge.  BFS fans out level by level and finds the shortest route; "
            "you must remember which rooms you have already been in.  Map your "
            "problem onto rooms and doors."
        ),
        skeleton=(
            "from collections import deque\n"
            "def solve(start, goal):\n"
            "    q = deque([start])\n"
            "    seen = {start}\n"
            "    while q:\n"
            "        node = q.popleft()\n"
            "        # TODO: check goal, enqueue neighbors\n"
        ),
    ),
    Topic(
        key="concurrency",
        label="concurrency and threads",
        complexity=0.85,
        keywords=["thread", "concurrency", "race", "deadlock", "mutex", "atomic",
                  "async", "await", "parallel"],
        concept_question=(
            "Which shared value can two tasks touch at the same time?  What "
            "must happen in one unbroken step?"
        ),
        plan_steps=[
            "Find the shared state that tasks read and write.",
            "Identify the critical section that must be atomic.",
            "Add the smallest lock around just that section.",
            "Check for lock ordering to avoid deadlock.",
        ],
        analogy=(
            "Related idea: two people writing in one shared notebook.  If both "
            "write on the same line at once the result is a mess; each must "
            "finish their line before the other starts.  Your shared state is "
            "that notebook."
        ),
        skeleton=(
            "with lock:\n"
            "    # TODO: read-modify-write the shared value atomically\n"
        ),
    ),
    Topic(
        key="regex",
        label="regular expressions",
        complexity=0.5,
        keywords=["regex", "regular expression", "pattern", "capture group"],
        concept_question=(
            "Write the pattern you are matching in plain words first: what "
            "starts it, what is optional, and what must it end with?"
        ),
        plan_steps=[
            "Describe the target text shape in words.",
            "Build the pattern piece by piece, testing each part.",
            "Add groups for the parts you want to pull out.",
            "Handle empty or missing matches explicitly.",
        ],
        analogy=(
            "Related idea: extracting phone numbers.  A number is three digits, "
            "a dash, three digits, a dash, four digits:  \\d{3}-\\d{3}-\\d{4}.  "
            "Describe your target's shape just as precisely."
        ),
        skeleton=(
            "pattern = r'<your pattern here>'\n"
            "m = re.search(pattern, text)\n"
            "if m:\n"
            "    # TODO: pull the captured group(s) you need\n"
        ),
    ),
    Topic(
        key="sql",
        label="SQL and databases",
        complexity=0.55,
        keywords=["sql", "join", "group by", "query", "table", "foreign key",
                  "aggregate"],
        concept_question=(
            "Which tables hold the data you need, and what connects a row in "
            "one table to a row in another?"
        ),
        plan_steps=[
            "List the columns you need and which tables they live in.",
            "Write the JOIN condition that links the tables.",
            "Add filters (WHERE) and grouping (GROUP BY) last.",
            "Run it against one known row to check the result.",
        ],
        analogy=(
            "Related idea: 'total sales per customer'.  You join orders to "
            "customers on the customer id, then GROUP BY the customer and SUM "
            "the amounts.  The join key is the linchpin — find yours."
        ),
        skeleton=(
            "SELECT <columns>\n"
            "FROM <main table>\n"
            "JOIN <other table> ON <link condition>\n"
            "WHERE <filter>\n"
            "# TODO: add GROUP BY / ORDER BY if needed\n"
        ),
    ),
    Topic(
        key="oop",
        label="objects and classes",
        complexity=0.5,
        keywords=["class", "object", "instance", "method", "inheritance",
                  "constructor", "attribute", "interface"],
        concept_question=(
            "What *state* does each object hold, and what *behaviour* should "
            "it expose?  Which behaviour belongs to the class vs. the caller?"
        ),
        plan_steps=[
            "Name the fields (state) each object needs.",
            "Write the constructor that sets them up.",
            "Add one method per responsibility, not one big method.",
            "Decide if a subclass or an interface removes duplication.",
        ],
        analogy=(
            "Related idea: modelling a bank account.  An account holds a "
            "balance (state) and exposes deposit/withdraw (behaviour).  The "
            "balance is private; callers go through methods.  Find your object's "
            "state and its two or three behaviours."
        ),
        skeleton=(
            "class Thing:\n"
            "    def __init__(self, ...):\n"
            "        # TODO: set up the object's state\n"
            "    def do_something(self, ...):\n"
            "        # TODO: implement one behaviour\n"
        ),
    ),
    Topic(
        key="error-handling",
        label="error handling",
        complexity=0.4,
        keywords=["exception", "try", "except", "error", "throw", "raise",
                  "validation"],
        concept_question=(
            "Which failure can happen here that is outside your control, and "
            "what should the program do instead of crashing?"
        ),
        plan_steps=[
            "Identify the operation that can fail.",
            "Catch the specific error, not a blanket one.",
            "Decide the fallback or the message to show.",
            "Let truly unexpected errors still surface.",
        ],
        analogy=(
            "Related idea: reading a file that may not exist.  You try to open "
            "it and, only if it is missing, fall back to a default.  The idea "
            "is to handle the *known* failure narrowly and keep going."
        ),
        skeleton=(
            "try:\n"
            "    <risky operation>\n"
            "except <SpecificError>:\n"
            "    # TODO: fall back or report a useful message\n"
        ),
    ),
]


# A fallback used when no topic keyword matches.  It keeps the hint ladder
# functional even for subjects the tutor does not know well.
_GENERIC = Topic(
    key="general",
    label="general problem solving",
    complexity=0.5,
    keywords=[],
    concept_question=(
        "Restate the problem in one sentence.  What is the input, and what "
        "exactly must the output be?"
    ),
    plan_steps=[
        "Restate the input and output precisely.",
        "Solve a tiny example by hand and write down your steps.",
        "Turn those steps into a general rule.",
        "Test the rule on a second, slightly harder example.",
    ],
    analogy=(
        "A useful habit: solve the smallest possible case by hand first, then "
        "the second smallest.  The difference between them usually reveals the "
        "general rule you need."
    ),
    skeleton=(
        "# First: write the steps you would do by hand as comments.\n"
        "# Then: turn each comment into code.\n"
        "# TODO: fill in the first step\n"
    ),
)


def _count_matches(text: str, keywords: List[str]) -> int:
    low = text.lower()
    return sum(1 for kw in keywords if kw in low)


def classify_topic(text: str) -> Topic:
    """Return the best matching topic for a prompt, or the generic fallback."""
    best: Topic = _GENERIC
    best_hits = 0
    for topic in TOPICS:
        hits = _count_matches(text, topic.keywords)
        if hits > best_hits:
            best = topic
            best_hits = hits
    return best
